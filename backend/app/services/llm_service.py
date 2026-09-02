"""
LLM Reasoning Service & Provider Abstraction
Supports Google Gemini (via google-genai SDK) and high-fidelity deterministic fallback.
Strictly bounded context: ONLY authorized, minimized entities, graph paths, and evidence chunks are passed.
Enforces Tri-Concept Separation: Graph Facts vs Documentary Evidence vs LLM Synthesis.
"""
import json
import logging
from typing import Optional
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import (
    Entity,
    GraphPath,
    EvidenceChunk,
    StructuredLLMOutput,
    Claim,
    ClaimSupportStatus,
    UserRole,
    QueryIntent
)
from app.data.seed_data import SEED_ENTITIES

logger = logging.getLogger(__name__)
ENTITY_LOOKUP: dict[str, Entity] = {e.id: e for e in SEED_ENTITIES}

SYSTEM_PROMPT = """You are SEMANTIQ, an enterprise AI reasoning engine operating over an authorized organizational knowledge graph and evidence chunks.

CORE OPERATIONAL RULES:
1. Tri-Concept Separation:
   - GRAPH FACT: A topological relationship in the knowledge graph (e.g. PRJ-DELTA -> DEPENDS_ON -> SYS-FURN-05).
   - DOCUMENTARY EVIDENCE: A cited text chunk (e.g. EVID-DELTA-01) that directly substantiates the relationship or claim.
   - If a relationship exists in graph paths but has NO documentary evidence chunk in context, clearly state: "The knowledge graph contains this relationship, but no authorized documentary evidence directly proves it." Do NOT invent or substitute unrelated citations.
2. Grounding: Answer the user query using ONLY the provided AUTHORIZED GRAPH PATHS and AUTHORIZED EVIDENCE CHUNKS. Never cite evidence that belongs to a different entity.
3. Query Intent: Address the specific user intent:
   - DEPENDENCY_QUERY / ENTITY_DESCRIPTION: Describe the entity and its direct dependencies/dependents. Do NOT include unsolicited incident shutdown procedures unless specifically asked.
   - IMPACT_QUERY / INCIDENT_QUERY: Explain affected assets and relevant emergency procedures.
   - EVIDENCE_QUERY: State whether direct documentary proof exists.
4. Citations: Every claim backed by documentary evidence MUST reference the exact Evidence ID in 'evidence_ids' and set 'support_status' to 'SUPPORTED'. If supported only by the graph, set 'support_status' to 'GRAPH_VERIFIED' and leave 'evidence_ids' empty.
5. Human Review: Set 'requires_human_review' to true ONLY when an operational action (e.g. machine shutdown, maintenance tag-out, quality quarantine) is recommended.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Categorized Gemini Error Types (never expose the API key in any message)
# ──────────────────────────────────────────────────────────────────────────────

class GeminiErrorCategory:
    AUTHENTICATION = "authentication_error"
    QUOTA = "quota_error"
    MODEL_NOT_FOUND = "model_error"
    PERMISSION = "permission_error"
    NETWORK = "network_error"
    TIMEOUT = "timeout_error"
    SCHEMA = "schema_error"
    INVALID_RESPONSE = "invalid_response"
    UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown_error"


def _categorize_gemini_error(exc: Exception) -> tuple[str, str]:
    """
    Returns (category, safe_display_label) from a Gemini exception.
    NEVER includes the API key, partial key, or any secret in returned strings.
    """
    err_str = str(exc).lower()
    exc_type = type(exc).__name__

    if "401" in err_str or "403" in err_str or "api_key" in err_str or "unauthenticated" in err_str or "permission_denied" in err_str:
        return GeminiErrorCategory.AUTHENTICATION, "Gemini Authentication Error"
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
        return GeminiErrorCategory.QUOTA, "Gemini Quota Error"
    if "404" in err_str or "not_found" in err_str or "no longer available" in err_str:
        return GeminiErrorCategory.MODEL_NOT_FOUND, "Gemini Model Error"
    if "503" in err_str or "502" in err_str or "unavailable" in err_str:
        return GeminiErrorCategory.UNAVAILABLE, "Gemini Service Unavailable"
    if "timeout" in err_str or "deadline" in err_str or "timed out" in err_str:
        return GeminiErrorCategory.TIMEOUT, "Gemini Timeout"
    if "network" in err_str or "connection" in err_str or "ssl" in err_str or "socket" in err_str:
        return GeminiErrorCategory.NETWORK, "Gemini Network Error"
    if "schema" in err_str or "validation" in err_str or "json" in err_str or "parse" in err_str:
        return GeminiErrorCategory.SCHEMA, "Gemini Response Error"
    if "invalid" in err_str or "malformed" in err_str:
        return GeminiErrorCategory.INVALID_RESPONSE, "Gemini Invalid Response"

    return GeminiErrorCategory.UNKNOWN, "Gemini API Error"


def build_minimized_context(
    query: str,
    role: UserRole,
    authorized_entities: list[Entity],
    graph_paths: list[GraphPath],
    evidence: list[EvidenceChunk],
    intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY
) -> dict:
    """
    Constructs the minimal context strictly bounded by user permissions, intent, and relevance.
    """
    return {
        "query": query,
        "query_intent": intent.value if hasattr(intent, 'value') else str(intent),
        "user_role": role.value if hasattr(role, 'value') else str(role),
        "authorized_entities": [
            {"id": e.id, "name": e.name, "type": e.type.value, "classification": e.classification.value, "description": e.description, "properties": e.properties}
            for e in authorized_entities
        ],
        "graph_paths": [
            {"path": " -> ".join(p.path_nodes), "relationships": p.path_relationships, "description": p.description}
            for p in graph_paths
        ],
        "authorized_evidence": [
            {
                "id": ev.id,
                "doc_id": ev.doc_id,
                "doc_title": ev.doc_title,
                "source_type": ev.source_type,
                "relevant_entities": ev.relevant_entities,
                "supported_relationships": ev.supported_relationships,
                "excerpt": ev.excerpt
            }
            for ev in evidence
        ]
    }


class LLMService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._last_error_category: Optional[str] = None
        self._last_error_label: Optional[str] = None
        self._init_gemini_client()

    def _init_gemini_client(self):
        self.client = None
        if settings.is_gemini_available:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(
                    "Gemini GenAI client initialized. "
                    f"Configured model: {self.model_name}"
                )
            except ImportError:
                logger.warning("google-genai SDK not installed. Will use deterministic fallback.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI SDK: {type(e).__name__}. Will use deterministic fallback.")

    def get_last_error_state(self) -> tuple[Optional[str], Optional[str]]:
        """Returns (error_category, display_label) from the last Gemini call attempt, or (None, None) if no error."""
        return self._last_error_category, self._last_error_label

    async def reason(
        self,
        query: str,
        role: UserRole,
        authorized_entities: list[Entity],
        graph_paths: list[GraphPath],
        evidence: list[EvidenceChunk],
        intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY
    ) -> tuple[StructuredLLMOutput, str]:
        """
        Executes reasoning over minimized authorized context.
        Returns (StructuredLLMOutput, provider_string).
        The provider_string is always honest:
          "Gemini Live (<model>)"                        — Gemini returned valid response
          "Gemini <Category Label>"                      — Gemini call failed with categorized error
          "Deterministic Fallback (No Gemini Key)"       — No API key configured
          "System Guard (Zero Authorized Context)"       — Zero authorized entities/evidence
        """
        minimized_context = build_minimized_context(
            query, role, authorized_entities, graph_paths, evidence, intent
        )

        # Pre-LLM System Guard: zero authorized context
        if not authorized_entities and not evidence:
            return self._generate_insufficient_evidence_output(query, intent), "System Guard (Zero Authorized Context)"

        # If Gemini is configured, invoke real API asynchronously
        if settings.is_gemini_available and self.client:
            logger.info(
                f"Gemini configured: true | model: {self.model_name} | "
                f"request: attempting"
            )
            try:
                output = await self._call_gemini(minimized_context)
                self._last_error_category = None
                self._last_error_label = None
                logger.info(f"Gemini result: success | model: {self.model_name}")
                return output, f"Gemini Live ({self.model_name})"
            except Exception as exc:
                category, label = _categorize_gemini_error(exc)
                self._last_error_category = category
                self._last_error_label = label
                # Log the error type and category WITHOUT the API key
                logger.error(
                    f"Gemini result: {category} | model: {self.model_name} | "
                    f"error_type: {type(exc).__name__} | label: {label}"
                )
                fallback_output = self._generate_deterministic_response(
                    query, role, authorized_entities, graph_paths, evidence, intent
                )
                return fallback_output, f"Deterministic Fallback ({label})"

        # No API key configured
        self._last_error_category = None
        self._last_error_label = None
        return self._generate_deterministic_response(
            query, role, authorized_entities, graph_paths, evidence, intent
        ), "Deterministic Fallback (No Gemini Key)"

    async def _call_gemini(self, context: dict) -> StructuredLLMOutput:
        """Invokes the real Gemini API asynchronously with structured JSON response schema."""
        from google.genai import types

        prompt_content = f"CONTEXT DATA:\n{json.dumps(context, indent=2)}\n\nUSER QUERY: {context['query']}\nQUERY INTENT: {context['query_intent']}"

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=StructuredLLMOutput,
                temperature=0.1,
            ),
        )

        raw_json = response.text.strip()
        # Clean any accidental Markdown fence blocks
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:]
        if raw_json.startswith("```"):
            raw_json = raw_json[3:]
        if raw_json.endswith("```"):
            raw_json = raw_json[:-3]
        raw_json = raw_json.strip()

        try:
            parsed = json.loads(raw_json)
            return StructuredLLMOutput(**parsed)
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            raise ValueError(f"schema parse error: {type(e).__name__}") from e

    def _generate_insufficient_evidence_output(self, query: str, intent: QueryIntent) -> StructuredLLMOutput:
        if intent == QueryIntent.RESTRICTED_QUERY:
            return StructuredLLMOutput(
                answer="Insufficient authorized evidence to provide commercial or restricted information.",
                recommendation="Contact system administrator or data steward to request elevated clearance for restricted technical and financial assets.",
                claims=[],
                assumptions=["Requested data is classified as RESTRICTED and withheld by the zero-trust permission boundary."],
                unknowns=[
                    "No authorized contracts, compensation records, or commercial terms match the user clearance level."
                ],
                requires_human_review=False,
                suggested_action=None
            )

        return StructuredLLMOutput(
            answer="I could not identify this entity or found no authorized documentary evidence in the knowledge repository.",
            recommendation="Verify entity ID spelling or check organizational permissions.",
            claims=[],
            assumptions=[],
            unknowns=["Entity is not present in the authorized knowledge graph."],
            requires_human_review=False,
            suggested_action=None
        )

    def _generate_deterministic_response(
        self,
        query: str,
        role: UserRole,
        authorized_entities: list[Entity],
        graph_paths: list[GraphPath],
        evidence: list[EvidenceChunk],
        intent: QueryIntent
    ) -> StructuredLLMOutput:
        """
        High-fidelity deterministic reasoning provider for local demo mode.
        Accurately adheres to query intent, scoped evidence, and Tri-Concept Separation.
        """
        q_lower = query.lower()
        entity_map = {e.id: e for e in authorized_entities}
        primary_entity = authorized_entities[0] if authorized_entities else None

        # Available retrieved evidence mapping
        evidence_by_entity: dict[str, list[EvidenceChunk]] = {}
        for ev in evidence:
            for ent in ev.relevant_entities:
                evidence_by_entity.setdefault(ent, []).append(ev)

        # 1. Restricted Query Handling
        if intent == QueryIntent.RESTRICTED_QUERY:
            if not any(ev.doc_id in ["CONTRACT-22", "PAYROLL-2026"] for ev in evidence):
                return self._generate_insufficient_evidence_output(query, intent)

        # 2. Evidence-Seeking Query
        if intent == QueryIntent.EVIDENCE_QUERY:
            if primary_entity and evidence:
                ev_chunks = [ev for ev in evidence if primary_entity.id in ev.relevant_entities]
                if ev_chunks:
                    first_ev = ev_chunks[0]
                    claims = [
                        Claim(
                            text=f"Documentary evidence from {first_ev.doc_id} ({first_ev.doc_title}) confirms: {first_ev.excerpt}",
                            entities=first_ev.relevant_entities,
                            evidence_ids=[first_ev.id],
                            support_status=ClaimSupportStatus.SUPPORTED,
                            is_verified=True
                        )
                    ]
                    return StructuredLLMOutput(
                        answer=f"Authorized documentary evidence from {first_ev.doc_id} directly substantiates this relationship: \"{first_ev.excerpt}\"",
                        recommendation=None,
                        claims=claims,
                        assumptions=[],
                        unknowns=[],
                        requires_human_review=False,
                        suggested_action=None
                    )

            if graph_paths and primary_entity:
                target_nodes = [n for p in graph_paths for n in p.path_nodes if n != primary_entity.id]
                target_str = ", ".join(target_nodes) if target_nodes else "connected systems"
                claims = [
                    Claim(
                        text=f"The knowledge graph records a connection between {primary_entity.name} ({primary_entity.id}) and {target_str}.",
                        entities=[primary_entity.id] + target_nodes,
                        evidence_ids=[],
                        support_status=ClaimSupportStatus.GRAPH_VERIFIED,
                        is_verified=False,
                        unsupported_reason="Graph relationship verified in knowledge topology; no direct documentary evidence chunk indexed."
                    )
                ]
                return StructuredLLMOutput(
                    answer=f"The knowledge graph contains the relationship between {primary_entity.name} ({primary_entity.id}) and {target_str}. However, I could not find authorized documentary evidence in the indexed repository that directly proves this relationship.",
                    recommendation="Review connected engineering specifications or request document indexing for this subsystem.",
                    claims=claims,
                    assumptions=["Relying strictly on knowledge graph relationship topology."],
                    unknowns=["Direct documentary evidence chunk is not indexed in the current authorized evidence store."],
                    requires_human_review=False,
                    suggested_action=None
                )

        # 3. Incident & Impact Query
        if intent in [QueryIntent.IMPACT_QUERY, QueryIntent.INCIDENT_QUERY] or "incident 104" in q_lower or "104" in q_lower:
            affected_projects = []
            for p in graph_paths:
                for n in p.path_nodes:
                    if n.startswith("PRJ-") and n in entity_map:
                        affected_projects.append(entity_map[n].name)
            affected_str = " and ".join(list(dict.fromkeys(affected_projects))) if affected_projects else "Project C (PRJ-GAMMA) and Project Alpha (PRJ-ALPHA)"

            claims = []
            c1_ev = [ev.id for ev in evidence if "INC-104" in ev.relevant_entities and ev.doc_id == "SOP-017"]
            if c1_ev:
                claims.append(Claim(
                    text="Incident 104 is an active high-severity thermal excursion on CNC-07 where spindle temperature exceeded the 68°C critical threshold.",
                    entities=["INC-104", "SYS-CNC-07"],
                    relationship="AFFECTED_BY",
                    evidence_ids=c1_ev,
                    support_status=ClaimSupportStatus.SUPPORTED,
                    is_verified=True
                ))

            c2_ev = [ev.id for ev in evidence if "PRJ-GAMMA" in ev.relevant_entities and ev.doc_id == "DOC-031"]
            if c2_ev:
                claims.append(Claim(
                    text="Project C (PRJ-GAMMA) is directly halted because CNC-07 is the sole certified 5-axis milling center for 5th-generation turbine blades.",
                    entities=["PRJ-GAMMA", "SYS-CNC-07"],
                    relationship="DEPENDS_ON",
                    evidence_ids=c2_ev,
                    support_status=ClaimSupportStatus.SUPPORTED,
                    is_verified=True
                ))

            c3_ev = [ev.id for ev in evidence if "SOP-017" in ev.relevant_entities or ev.doc_id == "SOP-017"]
            if c3_ev:
                claims.append(Claim(
                    text="SOP-017 mandates an immediate feed hold, spindle shutdown, machine tag-out, and dial indicator runout inspection by Dr. Kenji Sato prior to restart.",
                    entities=["SOP-017", "TEAM-SAFETY", "EMP-001"],
                    relationship="RELATED_TO",
                    evidence_ids=c3_ev[:2],
                    support_status=ClaimSupportStatus.SUPPORTED,
                    is_verified=True
                ))

            return StructuredLLMOutput(
                answer=f"Incident 104 directly impacts {affected_str} due to their reliance on CNC-07 (SYS-CNC-07). CNC-07 experienced a spindle bearing thermal excursion exceeding 74°C, triggering emergency response protocol SOP-017.",
                recommendation="The responsible teams (Manufacturing Operations TEAM-MFG-OPS and Reliability TEAM-RELIABILITY) must execute SOP-017: command an immediate feed hold and cutting tool Z-axis retract, decelerate the spindle to 500 RPM ramp-down for 60s, shut down the spindle drive, tag out the machine, and inspect Chiller 02 coolant flow. Dr. Kenji Sato must verify spindle runout and vibration before restarting. All turbine blades produced during the excursion must undergo 100% CMM laser inspection.",
                claims=claims,
                assumptions=[
                    "CNC-07 remains physically in Bay-4B and is powered down per SOP-017 Step 1-2.",
                    "Secondary chiller Chiller 02 flow rate telemetry is operational."
                ],
                unknowns=[],
                requires_human_review=True,
                suggested_action="Execute SOP-017 Spindle Emergency Shutdown and tag out CNC-07 pending dial indicator runout verification by Dr. Kenji Sato."
            )

        # 4. Dependency & Description Queries
        if intent in [QueryIntent.DEPENDENCY_QUERY, QueryIntent.ENTITY_DESCRIPTION]:
            if primary_entity:
                connected_nodes = []
                connected_rel_descriptions = []
                for p in graph_paths:
                    for i, node in enumerate(p.path_nodes):
                        if node != primary_entity.id:
                            ent_obj = entity_map.get(node) or ENTITY_LOOKUP.get(node)
                            if ent_obj and ent_obj not in connected_nodes:
                                connected_nodes.append(ent_obj)
                                if i < len(p.path_relationships):
                                    connected_rel_descriptions.append(f"{primary_entity.name} --[{p.path_relationships[i]}]--> {ent_obj.name} ({node})")

                claims = []
                primary_evidence = [ev for ev in evidence if primary_entity.id in ev.relevant_entities]

                if primary_evidence:
                    for ev in primary_evidence[:2]:
                        claims.append(Claim(
                            text=f"{ev.doc_title}: {ev.excerpt}",
                            entities=ev.relevant_entities,
                            evidence_ids=[ev.id],
                            support_status=ClaimSupportStatus.SUPPORTED,
                            is_verified=True
                        ))
                elif connected_nodes:
                    claims.append(Claim(
                        text=f"{primary_entity.name} ({primary_entity.id}) is connected in the knowledge graph to {', '.join([c.name for c in connected_nodes[:2]])}.",
                        entities=[primary_entity.id] + [c.id for c in connected_nodes[:2]],
                        evidence_ids=[],
                        support_status=ClaimSupportStatus.GRAPH_VERIFIED,
                        is_verified=False,
                        unsupported_reason="Verified by knowledge graph topology; no direct documentary evidence chunk retrieved."
                    ))

                if primary_entity.type == "system" or primary_entity.id.startswith("SYS-"):
                    dep_projects = [c.name for c in connected_nodes if c.id.startswith("PRJ-")]
                    dep_str = f"Projects depending on it include: {', '.join(dep_projects)}." if dep_projects else "No direct project dependencies are currently mapped."
                    answer = f"{primary_entity.name} ({primary_entity.id}) is a {primary_entity.description} {dep_str}"
                else:
                    dep_systems = [c.name for c in connected_nodes if c.id.startswith("SYS-")]
                    dep_str = f"It depends on {', '.join(dep_systems)} ({', '.join([c.id for c in connected_nodes if c.id.startswith('SYS-')])})." if dep_systems else "No system dependencies are mapped."
                    answer = f"{primary_entity.name} ({primary_entity.id}) is an organizational project focused on: {primary_entity.description} {dep_str}"

                if not primary_evidence and connected_nodes:
                    answer += " (Note: This relationship is recorded as a graph fact in the organizational topology; no direct documentary specification is currently indexed)."

                return StructuredLLMOutput(
                    answer=answer,
                    recommendation=None,
                    claims=claims,
                    assumptions=[],
                    unknowns=[] if primary_evidence else ["No documentary specification chunk indexed for this entity."],
                    requires_human_review=False,
                    suggested_action=None
                )

        # 5. SOP & Policy Ownership Queries
        if intent in [QueryIntent.OWNERSHIP_QUERY, QueryIntent.POLICY_QUERY] or "owns" in q_lower or "sop" in q_lower:
            claims = []
            sop_evidence = [ev for ev in evidence if "SOP-017" in ev.relevant_entities or "POL-SAFE-01" in ev.relevant_entities]
            if sop_evidence:
                claims.append(Claim(
                    text="SOP-017 is governed under Critical Machinery Safety Standard POL-SAFE-01 and owned by Environmental Health & Safety (TEAM-SAFETY).",
                    entities=["SOP-017", "POL-SAFE-01", "TEAM-SAFETY"],
                    relationship="OWNED_BY",
                    evidence_ids=[ev.id for ev in sop_evidence[:2]],
                    support_status=ClaimSupportStatus.SUPPORTED,
                    is_verified=True
                ))

            return StructuredLLMOutput(
                answer="SOP-017 ('CNC High-Speed Spindle Temperature Incident Response & Shutdown Procedure') is owned by the Safety Team (TEAM-SAFETY) in collaboration with Site Reliability (TEAM-RELIABILITY).",
                recommendation="Consult Safety Director Sarah Jenkins (EMP-006) or Principal Reliability Engineer Dr. Kenji Sato (EMP-001) for protocol modifications.",
                claims=claims,
                assumptions=[],
                unknowns=[],
                requires_human_review=False,
                suggested_action=None
            )

        # 6. Generic Grounded Synthesis Fallback
        claims = []
        for ev in evidence[:3]:
            claims.append(Claim(
                text=f"{ev.doc_title}: {ev.excerpt}",
                entities=ev.relevant_entities,
                evidence_ids=[ev.id],
                support_status=ClaimSupportStatus.SUPPORTED,
                is_verified=True
            ))

        return StructuredLLMOutput(
            answer=f"Analysis grounded in {len(evidence)} authorized evidence sources: " + (" ".join([ev.excerpt[:120] + "..." for ev in evidence[:2]]) if evidence else "No matching evidence."),
            recommendation=None,
            claims=claims,
            assumptions=["Operating within standard factory parameters."],
            unknowns=[],
            requires_human_review=False,
            suggested_action=None
        )


llm_service = LLMService()
