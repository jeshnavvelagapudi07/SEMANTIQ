"""
Confidence Scoring Service
Deterministic, calibrated application-level confidence model with explainable breakdown.
Distinguishes Graph Facts, Documentary Grounding, and Entity Alignment.
"""
from app.models.schemas import (
    ConfidenceScore,
    ConfidenceLevel,
    DecisionFactor,
    EvidenceChunk,
    GraphPath,
    Claim,
    ClaimSupportStatus,
    Entity,
    QueryIntent
)


class ConfidenceService:
    @staticmethod
    def calculate(
        identified_entities: list[Entity],
        graph_paths: list[GraphPath],
        retrieved_evidence: list[EvidenceChunk],
        validated_claims: list[Claim],
        citation_validity_rate: float,
        intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY,
        is_insufficient_evidence: bool = False
    ) -> ConfidenceScore:
        """
        Calculates calibrated deterministic application-level confidence.
        """
        if is_insufficient_evidence:
            return ConfidenceScore(
                score=15.0,
                level=ConfidenceLevel.LOW,
                explanation="Low confidence due to insufficient authorized evidence or restricted clearance boundary.",
                breakdown={
                    "evidence_quality": 0.0,
                    "graph_path_strength": 0.0,
                    "citation_validity": 0.0,
                    "retrieval_coverage": 15.0,
                    "penalty": 0.0
                },
                decision_factors=[
                    DecisionFactor(
                        factor="Zero-Trust Permission Guard",
                        impact="NEGATIVE",
                        details="No authorized documents or graph records matched the requested query entities."
                    )
                ]
            )

        decision_factors: list[DecisionFactor] = []

        # 1. Documentary Evidence Quality (0 - 30 pts)
        ev_count = len(retrieved_evidence)
        if ev_count >= 3:
            ev_score = 30.0
            decision_factors.append(DecisionFactor(
                factor="Documentary Evidence Depth",
                impact="POSITIVE",
                details=f"{ev_count} authorized documentary evidence sources retrieved (+30 pts)."
            ))
        elif ev_count == 2:
            ev_score = 22.0
            decision_factors.append(DecisionFactor(
                factor="Documentary Evidence Depth",
                impact="POSITIVE",
                details="2 authorized documentary evidence sources retrieved (+22 pts)."
            ))
        elif ev_count == 1:
            ev_score = 15.0
            decision_factors.append(DecisionFactor(
                factor="Documentary Evidence Depth",
                impact="NEUTRAL",
                details="1 authorized documentary evidence source retrieved (+15 pts)."
            ))
        else:
            ev_score = 0.0
            impact = "NEGATIVE" if intent == QueryIntent.EVIDENCE_QUERY else "NEUTRAL"
            decision_factors.append(DecisionFactor(
                factor="Documentary Evidence Depth",
                impact=impact,
                details="No documentary evidence text chunks indexed; relying solely on graph topology (0 pts)."
            ))

        # 2. Graph Path Topology (0 - 30 pts)
        path_count = len(graph_paths)
        if path_count > 0:
            min_hops = min(p.length for p in graph_paths)
            if min_hops <= 2:
                graph_score = 30.0
                decision_factors.append(DecisionFactor(
                    factor="Graph Path Topology",
                    impact="POSITIVE",
                    details=f"Direct {min_hops}-hop causal/dependency path verified in knowledge graph (+30 pts)."
                ))
            elif min_hops == 3:
                graph_score = 22.0
                decision_factors.append(DecisionFactor(
                    factor="Graph Path Topology",
                    impact="POSITIVE",
                    details="3-hop graph dependency path verified (+22 pts)."
                ))
            else:
                graph_score = 15.0
                decision_factors.append(DecisionFactor(
                    factor="Graph Path Topology",
                    impact="NEUTRAL",
                    details=f"{min_hops}-hop graph path traversed (+15 pts)."
                ))
        else:
            graph_score = 10.0 if identified_entities else 0.0
            decision_factors.append(DecisionFactor(
                factor="Graph Path Topology",
                impact="NEUTRAL",
                details="Direct entity attributes matched without multi-hop path (+10 pts)."
            ))

        # 3. Citation Validity & Grounding (0 - 25 pts)
        has_graph_only_claims = any(c.support_status == ClaimSupportStatus.GRAPH_VERIFIED for c in validated_claims)
        if ev_count > 0:
            citation_score = round(25.0 * citation_validity_rate, 1)
            if citation_validity_rate >= 0.99:
                decision_factors.append(DecisionFactor(
                    factor="Citation Grounding",
                    impact="POSITIVE",
                    details="100% of LLM claims backed by verified documentary citations (+25 pts)."
                ))
            else:
                decision_factors.append(DecisionFactor(
                    factor="Citation Grounding",
                    impact="NEUTRAL",
                    details=f"{round(citation_validity_rate * 100)}% citation verification rate (+{citation_score} pts)."
                ))
        elif has_graph_only_claims:
            citation_score = 10.0
            decision_factors.append(DecisionFactor(
                factor="Citation Grounding",
                impact="NEUTRAL",
                details="Claims verified against Knowledge Graph topology (+10 pts)."
            ))
        else:
            citation_score = 0.0
            decision_factors.append(DecisionFactor(
                factor="Citation Grounding",
                impact="NEGATIVE",
                details="Zero verified citations (0 pts)."
            ))

        # 4. Entity Resolution & Intent Alignment (0 - 15 pts)
        if len(identified_entities) > 0:
            coverage_score = 15.0
            decision_factors.append(DecisionFactor(
                factor="Entity Resolution",
                impact="POSITIVE",
                details=f"{len(identified_entities)} key entities resolved and authorized (+15 pts)."
            ))
        else:
            coverage_score = 5.0
            decision_factors.append(DecisionFactor(
                factor="Entity Resolution",
                impact="NEUTRAL",
                details="Generic query matching without direct entity resolution (+5 pts)."
            ))

        # 5. Unsupported Claims Penalty (-15 pts each)
        unsupported_count = sum(1 for c in validated_claims if not c.is_verified and c.support_status != ClaimSupportStatus.GRAPH_VERIFIED)
        penalty = unsupported_count * 15.0
        if penalty > 0:
            decision_factors.append(DecisionFactor(
                factor="Unsupported Claim Penalty",
                impact="NEGATIVE",
                details=f"{unsupported_count} unsupported claim(s) detected (-{penalty} pts)."
            ))

        raw_total = ev_score + graph_score + citation_score + coverage_score - penalty
        final_score = max(0.0, min(100.0, round(raw_total, 1)))

        # Cap confidence if documentary evidence is missing for an EVIDENCE_QUERY
        if intent == QueryIntent.EVIDENCE_QUERY and ev_count == 0:
            final_score = min(final_score, 45.0)

        if final_score >= 75.0:
            level = ConfidenceLevel.HIGH
            explanation = "High confidence: Causal graph path verified and fully grounded in authorized documentary evidence."
        elif final_score >= 45.0:
            level = ConfidenceLevel.MEDIUM
            explanation = "Medium confidence: Graph topology verified; documentary evidence is limited or relying on structural facts."
        else:
            level = ConfidenceLevel.LOW
            explanation = "Low confidence: Insufficient documentary grounding or missing entity relationships."

        return ConfidenceScore(
            score=final_score,
            level=level,
            explanation=explanation,
            breakdown={
                "evidence_quality": ev_score,
                "graph_path_strength": graph_score,
                "citation_validity": citation_score,
                "retrieval_coverage": coverage_score,
                "penalty": penalty
            },
            decision_factors=decision_factors
        )


confidence_service = ConfidenceService()
