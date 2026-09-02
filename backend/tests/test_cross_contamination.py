"""
Tests for Zero Cross-Entity Contamination and Intent-Driven Synthesis
"""
import pytest
import asyncio
from app.models.schemas import UserRole, QueryRequest, QueryIntent
from app.services.intent_service import intent_service
from app.services.retrieval_service import retrieval_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.validation_service import validation_service
from app.services.confidence_service import confidence_service


@pytest.mark.asyncio
async def test_project_delta_zero_gamma_contamination():
    """
    Test 3 & Negative Test: Querying Project Delta must NOT retrieve or cite
    Project Gamma, CNC-07, thermal expansion, or SOP-017 evidence.
    """
    role = UserRole.OPERATIONS_ENGINEER
    query = "What is Project Delta and which system does it depend on?"
    
    intent, _ = intent_service.classify_intent(query)
    assert intent == QueryIntent.DEPENDENCY_QUERY

    authorized_entities, _ = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in authorized_entities]
    assert "PRJ-DELTA" in auth_ids
    assert "PRJ-GAMMA" not in auth_ids

    paths = graph_service.traverse_for_entities(auth_ids, role, max_hops=3)
    evidence, _ = retrieval_service.retrieve_evidence(query, role, paths, authorized_entities, intent=intent)

    # Verify zero Project Gamma / CNC-07 evidence
    for ev in evidence:
        assert "PRJ-GAMMA" not in ev.relevant_entities
        assert ev.id not in ["EVID-031-01", "EVID-031-02", "EVID-017-01", "EVID-023-01"]

    llm_output, _ = await llm_service.reason(query, role, authorized_entities, paths, evidence, intent=intent)
    
    # Assert synthesized answer is about Project Delta and SYS-FURN-05
    assert "Delta" in llm_output.answer or "PRJ-DELTA" in llm_output.answer
    assert "FURN-05" in llm_output.answer or "Induction Furnace" in llm_output.answer
    assert "Project Gamma" not in llm_output.answer
    assert "Incident 104" not in llm_output.answer
    assert llm_output.recommendation is None  # No unsolicited shutdown recommendation!

    # Validate claims
    validated_claims, val_status, _, val_rate = validation_service.validate_citations(llm_output.claims, evidence, role)
    assert val_status in ["PASSED", "WARNING"]
    for c in validated_claims:
        assert "Project Gamma" not in c.text
        for eid in c.evidence_ids:
            assert eid not in ["EVID-031-01", "EVID-017-01"]


@pytest.mark.asyncio
async def test_project_zeta_zero_gamma_contamination():
    """
    Test 4 & Negative Test: Querying Project Zeta must NOT retrieve or cite
    Project Gamma or Incident 104.
    """
    role = UserRole.OPERATIONS_ENGINEER
    query = "What is Project Zeta and which systems does it depend on?"

    intent, _ = intent_service.classify_intent(query)
    authorized_entities, _ = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in authorized_entities]
    assert "PRJ-ZETA" in auth_ids

    paths = graph_service.traverse_for_entities(auth_ids, role, max_hops=3)
    evidence, _ = retrieval_service.retrieve_evidence(query, role, paths, authorized_entities, intent=intent)

    for ev in evidence:
        assert "PRJ-GAMMA" not in ev.relevant_entities
        assert ev.id != "EVID-031-01"

    llm_output, _ = await llm_service.reason(query, role, authorized_entities, paths, evidence, intent=intent)
    assert "Zeta" in llm_output.answer or "PRJ-ZETA" in llm_output.answer
    assert "Project Gamma" not in llm_output.answer
    assert "Incident 104" not in llm_output.answer


@pytest.mark.asyncio
async def test_cnc07_dependency_query_intent_respect():
    """
    Test 1: 'What is CNC-07 and what projects depend on it?'
    Must explain CNC-07 and dependent projects (Gamma and Alpha),
    WITHOUT turning the answer primarily into an Incident 104 emergency shutdown procedure.
    """
    role = UserRole.OPERATIONS_ENGINEER
    query = "What is CNC-07 and what projects depend on it?"

    intent, _ = intent_service.classify_intent(query)
    assert intent == QueryIntent.DEPENDENCY_QUERY

    authorized_entities, _ = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in authorized_entities]
    assert "SYS-CNC-07" in auth_ids

    paths = graph_service.traverse_for_entities(auth_ids, role, max_hops=3)
    evidence, _ = retrieval_service.retrieve_evidence(query, role, paths, authorized_entities, intent=intent)

    llm_output, _ = await llm_service.reason(query, role, authorized_entities, paths, evidence, intent=intent)
    
    # Must answer about CNC-07 and dependencies
    assert "CNC-07" in llm_output.answer
    assert "Project C" in llm_output.answer or "Project Gamma" in llm_output.answer or "PRJ-GAMMA" in llm_output.answer
    assert "Project Alpha" in llm_output.answer or "PRJ-ALPHA" in llm_output.answer

    # Must NOT have unsolicited emergency shutdown action item
    assert llm_output.requires_human_review is False


@pytest.mark.asyncio
async def test_project_delta_evidence_grounding():
    """
    Test 5: 'What evidence proves that Project Delta depends on SYS-FURN-05?'
    Must return direct documentary evidence from DOC-FURN-05 (EVID-DELTA-01)
    and never substitute unrelated evidence (e.g. SOP-017, DOC-031).
    """
    role = UserRole.OPERATIONS_ENGINEER
    query = "What evidence proves that Project Delta depends on SYS-FURN-05?"

    intent, _ = intent_service.classify_intent(query)
    assert intent == QueryIntent.EVIDENCE_QUERY

    authorized_entities, _ = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in authorized_entities]
    assert "PRJ-DELTA" in auth_ids
    assert "SYS-FURN-05" in auth_ids

    paths = graph_service.traverse_for_entities(auth_ids, role, max_hops=3)
    evidence, _ = retrieval_service.retrieve_evidence(query, role, paths, authorized_entities, intent=intent)

    # Must find EVID-DELTA-01
    ev_ids = [ev.id for ev in evidence]
    assert "EVID-DELTA-01" in ev_ids
    assert "EVID-031-01" not in ev_ids
    assert "EVID-017-01" not in ev_ids

    llm_output, _ = await llm_service.reason(query, role, authorized_entities, paths, evidence, intent=intent)
    assert "DOC-FURN-05" in llm_output.answer or "EVID-DELTA-01" in str(llm_output.claims) or "Induction Furnace" in llm_output.answer
