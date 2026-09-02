"""
Intent Classification Service
Deterministically classifies user query intent to control downstream GraphRAG retrieval,
evidence prioritization, and structured synthesis.
"""
import re
from typing import Any
from app.models.schemas import QueryIntent


class IntentService:
    @staticmethod
    def classify_intent(query: str) -> tuple[QueryIntent, dict[str, Any]]:
        """
        Classifies query into a QueryIntent and extracts focal intent metadata.
        """
        q_lower = query.lower().strip()
        metadata: dict[str, Any] = {}

        # 1. Restricted Information Query Check
        restricted_patterns = [
            r"\bcontract\b", r"\bpricing\b", r"\bpenalt(y|ies)\b", r"\bsalar(y|ies)\b",
            r"\bbonus\b", r"\bcompensation\b", r"\bmaster supply agreement\b",
            r"\bpayroll\b", r"\bcommercial terms\b"
        ]
        if any(re.search(pat, q_lower) for pat in restricted_patterns):
            metadata["focal_category"] = "RESTRICTED_COMMERCIAL_OR_HR"
            return QueryIntent.RESTRICTED_QUERY, metadata

        # 2. Evidence Query Check (Explicitly asking for evidence / proof / documents)
        evidence_patterns = [
            r"what evidence", r"which evidence", r"show evidence", r"find evidence",
            r"what proof", r"prove that", r"evidence proves", r"evidence supports",
            r"documentary evidence", r"show me the evidence"
        ]
        if any(pat in q_lower for pat in evidence_patterns):
            metadata["requires_direct_evidence"] = True
            return QueryIntent.EVIDENCE_QUERY, metadata

        # 3. Ownership / Governance Query Check
        ownership_patterns = [
            r"who owns", r"which team owns", r"who is responsible", r"owned by",
            r"who leads", r"who is the lead", r"who manages", r"ownership of"
        ]
        if any(pat in q_lower for pat in ownership_patterns):
            metadata["focal_relation"] = "OWNED_BY"
            return QueryIntent.OWNERSHIP_QUERY, metadata

        # 4. Impact / Incident Query Check
        impact_patterns = [
            r"affected by", r"impact of", r"who is affected", r"which projects are affected",
            r"what is affected", r"impacted by", r"consequences of"
        ]
        if any(pat in q_lower for pat in impact_patterns):
            metadata["focal_relation"] = "AFFECTED_BY"
            return QueryIntent.IMPACT_QUERY, metadata

        incident_patterns = [
            r"incident\s*\d+", r"inc-\d+", r"thermal excursion", r"failure", r"anomaly",
            r"spindle overheat", r"what happened in incident"
        ]
        if any(re.search(pat, q_lower) for pat in incident_patterns) and not any(p in q_lower for p in ["what is cnc", "what is project"]):
            metadata["focal_type"] = "incident"
            return QueryIntent.INCIDENT_QUERY, metadata

        # 5. Policy / SOP / Procedure Query Check
        policy_patterns = [
            r"\bsop\b", r"standard operating procedure", r"procedure for", r"protocol for",
            r"how to shutdown", r"escalation procedure", r"what is the procedure",
            r"what should the responsible team do", r"action plan", r"steps to"
        ]
        if any(re.search(pat, q_lower) for pat in policy_patterns):
            metadata["focal_type"] = "procedure"
            return QueryIntent.POLICY_QUERY, metadata

        # 6. Dependency Query Check
        dependency_patterns = [
            r"depend(s)? on", r"dependenc(y|ies)", r"rel(y|ies) on", r"what projects depend on",
            r"which systems does it depend on", r"what system does .* depend on",
            r"what does .* use", r"uses", r"connected to"
        ]
        if any(re.search(pat, q_lower) for pat in dependency_patterns):
            metadata["focal_relation"] = "DEPENDS_ON"
            return QueryIntent.DEPENDENCY_QUERY, metadata

        # 7. Entity Description Check
        description_patterns = [
            r"^what is\b", r"^tell me about\b", r"^describe\b", r"^explain\b",
            r"^overview of\b", r"^details on\b", r"^summary of\b"
        ]
        if any(re.search(pat, q_lower) for pat in description_patterns):
            metadata["focal_task"] = "DESCRIPTION"
            return QueryIntent.ENTITY_DESCRIPTION, metadata

        # Default fallback
        return QueryIntent.GENERAL_KNOWLEDGE_QUERY, metadata


intent_service = IntentService()
