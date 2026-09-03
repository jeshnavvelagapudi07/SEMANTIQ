"""
Query Reasoning API Router
Main GraphRAG reasoning pipeline, path explanations, and grounded query endpoints.
Guarantees server-side identity & role resolution from cryptographic session tokens.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    ReasoningTrace,
    UserRole,
    GraphPath,
    ActionItem,
    QueryIntent,
    ClaimSupportStatus
)
from app.core.auth import get_current_user, resolve_effective_role, AuthUser
from app.services.intent_service import intent_service
from app.services.retrieval_service import retrieval_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.validation_service import validation_service
from app.services.confidence_service import confidence_service
from app.services.audit_service import audit_service
from app.services.action_service import action_service

router = APIRouter(prefix="/query", tags=["Query Reasoning"])


class ExplainPathRequest(BaseModel):
    source_id: str
    target_id: str
    role: Optional[UserRole] = None


class ExplainPathResponse(BaseModel):
    source_id: str
    target_id: str
    paths: list[GraphPath]
    explanation: str
    supporting_evidence: list[dict]


@router.post("", response_model=QueryResponse)
async def execute_query(
    req: QueryRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Executes the full Permission-Aware GraphRAG Query Pipeline:
    Query Intent -> Server-Side Role Resolution -> Entity Resolution -> Permission Filter ->
    Graph Traversal -> Evidence Ranking -> Context Minimization -> LLM Reasoning ->
    Citation Validation -> Confidence Scoring -> Action Hook -> Audit Log.
    """
    query_id = f"QRY-{uuid.uuid4().hex[:8].upper()}"

    # Step 0: Server-Side Identity & Role Resolution
    # CRITICAL: If an auth token is present, the server-resolved role and user_id MUST be used.
    # Any role sent by the client in request payload is completely ignored.
    effective_role, effective_user_id = resolve_effective_role(
        current_user,
        client_supplied_role=req.role,
        client_user_id=req.user_id
    )

    # Step 1: Query Intent Classification
    intent, intent_meta = intent_service.classify_intent(req.query)

    # Step 2: Entity Identification & Pre-LLM Permission Filter
    authorized_entities, filtered_entities = retrieval_service.identify_entities(req.query, effective_role)
    auth_entity_ids = [e.id for e in authorized_entities]

    # Step 3: Bounded Graph Traversal over Authorized Subgraph
    graph_paths = graph_service.traverse_for_entities(auth_entity_ids, effective_role, max_hops=req.max_hops)

    # Step 4: Extract Graph Facts (topological relationships)
    graph_facts = [
        f"{p.path_nodes[0]} -> [{p.path_relationships[0] if p.path_relationships else 'RELATED_TO'}] -> {p.path_nodes[1]}"
        for p in graph_paths if len(p.path_nodes) >= 2
    ]

    # Step 5: Scoped Hybrid Evidence Retrieval with Permission Pre-filtering and Intent Weighting
    evidence, filtered_evidence = retrieval_service.retrieve_evidence(
        req.query, effective_role, graph_paths, authorized_entities, intent=intent, top_k=5
    )

    all_filtered_details = filtered_entities + filtered_evidence
    filtered_items_count = len(all_filtered_details)

    # Step 6: LLM Reasoning over Minimized Authorized Context
    llm_output, provider_used = await llm_service.reason(
        req.query, effective_role, authorized_entities, graph_paths, evidence, intent=intent
    )

    # Step 7: Citation Grounding & Output Validation
    validated_claims, val_status, val_checks, citation_validity_rate = validation_service.validate_citations(
        llm_output.claims, evidence, effective_role
    )

    # Step 7b: Partition claims — only SUPPORTED and GRAPH_VERIFIED claims are presented
    # as grounded synthesis. UNSUPPORTED / INSUFFICIENT_EVIDENCE claims are segregated
    # into unsupported_claims so they never appear inside the grounded synthesis section.
    # NOTE: confidence_service receives the full validated_claims list (including unsupported)
    # so that the unsupported-claim penalty is still applied correctly.
    _GROUNDED_STATUSES = {ClaimSupportStatus.SUPPORTED, ClaimSupportStatus.GRAPH_VERIFIED}
    grounded_claims = [c for c in validated_claims if c.support_status in _GROUNDED_STATUSES]
    unsupported_claims = [c for c in validated_claims if c.support_status not in _GROUNDED_STATUSES]

    # Step 8: Application-Level Calibrated Confidence Calculation
    is_insufficient = (len(evidence) == 0 and len(authorized_entities) == 0) or "insufficient" in llm_output.answer.lower()
    confidence = confidence_service.calculate(
        authorized_entities,
        graph_paths,
        evidence,
        validated_claims,
        citation_validity_rate,
        intent=intent,
        is_insufficient_evidence=is_insufficient
    )

    # Step 9: Human-in-the-Loop Action Handling
    action_item: Optional[ActionItem] = None
    if llm_output.requires_human_review and llm_output.suggested_action:
        target_ent = auth_entity_ids[0] if auth_entity_ids else "SYSTEM"
        action_item = action_service.create_action(
            query_id=query_id,
            title=f"Review Action for {target_ent}",
            description=llm_output.suggested_action,
            target_entity=target_ent
        )

    # Step 10: Assemble Reasoning Trace (Safe metadata ONLY, zero hidden chain-of-thought)
    reasoning_trace = ReasoningTrace(
        query_intent=intent,
        identified_entities=[e.id for e in authorized_entities],
        authorized_entities=auth_entity_ids,
        filtered_entities_count=filtered_items_count,
        filtered_details=all_filtered_details,
        traversed_paths=graph_paths,
        graph_facts=graph_facts,
        retrieved_evidence_ids=[ev.id for ev in evidence],
        decision_factors=[f.details for f in confidence.decision_factors],
        validation_checks=val_checks,
        confidence=confidence,
        minimized_context_token_estimate=len(str(evidence)) // 4
    )

    # Step 11: Audit Trail Logging in SQLite
    audit_service.log_query(
        query_id=query_id,
        user_id=effective_user_id,
        user_role=effective_role,
        query=req.query,
        identified_entities=auth_entity_ids,
        authorized_entities=auth_entity_ids,
        filtered_entities_count=filtered_items_count,
        filtered_details=[f.model_dump() for f in all_filtered_details],
        graph_paths_count=len(graph_paths),
        evidence_ids=[ev.id for ev in evidence],
        llm_provider=provider_used,
        validation_status=val_status,
        confidence_score=confidence.score,
        confidence_level=confidence.level.value,
        recommendation=llm_output.recommendation,
        requires_human_review=llm_output.requires_human_review,
        action_id=action_item.id if action_item else None,
        action_status=action_item.status if action_item else None
    )

    # Step 12: Construct Missing Information list for insufficient evidence
    missing_info = None
    if is_insufficient:
        missing_info = [
            f"Filtered {filtered_items_count} item(s) requiring elevated clearance." if filtered_items_count > 0 else "No matching knowledge graph entities found in directory.",
            "Verify entity names or contact organizational administrator for access authorization."
        ]

    return QueryResponse(
        query_id=query_id,
        user_role=effective_role,
        user_id=effective_user_id,
        query=req.query,
        query_intent=intent,
        answer=llm_output.answer,
        recommendation=llm_output.recommendation,
        claims=grounded_claims,
        unsupported_claims=unsupported_claims,
        graph_paths=graph_paths,
        graph_facts=graph_facts,
        evidence=evidence,
        confidence=confidence,
        reasoning_trace=reasoning_trace,
        requires_human_review=llm_output.requires_human_review,
        action_item=action_item,
        filtered_items_count=filtered_items_count,
        filtered_summary=all_filtered_details,
        provider_used=provider_used,
        is_insufficient_evidence=is_insufficient,
        missing_information=missing_info
    )


@router.post("/explain-path", response_model=ExplainPathResponse)
async def explain_path(
    req: ExplainPathRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Finds and explains authorized multi-hop graph connections between source and target entities.
    Enforces server-side identity & role resolution.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=req.role)
    paths = graph_service.find_paths_between(req.source_id, req.target_id, effective_role, max_hops=4)
    if not paths:
        return ExplainPathResponse(
            source_id=req.source_id,
            target_id=req.target_id,
            paths=[],
            explanation=f"No authorized graph path found between '{req.source_id}' and '{req.target_id}' under role '{effective_role.value}'.",
            supporting_evidence=[]
        )

    # Fetch supporting authorized evidence along the path
    path_nodes = set()
    for p in paths:
        path_nodes.update(p.path_nodes)

    ent_objs, _ = retrieval_service.identify_entities(f"{req.source_id} {req.target_id}", effective_role)
    ev_chunks, _ = retrieval_service.retrieve_evidence(
        f"{req.source_id} {req.target_id}", effective_role, paths, ent_objs, top_k=4
    )

    # Format explanation
    p0 = paths[0]
    steps_desc = " -> ".join([f"{p0.path_nodes[i]} [{p0.path_relationships[i]}]" for i in range(len(p0.path_relationships))]) + f" -> {p0.path_nodes[-1]}"
    explanation = f"Connection verified in knowledge graph ({p0.length} hops): {steps_desc}."

    return ExplainPathResponse(
        source_id=req.source_id,
        target_id=req.target_id,
        paths=paths,
        explanation=explanation,
        supporting_evidence=[ev.model_dump() for ev in ev_chunks]
    )
