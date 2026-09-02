"""
Unit Tests for Confidence Scoring Service
Validates deterministic factor scoring, unsupported penalties, and confidence levels.
"""
from app.models.schemas import (
    Entity,
    EntityType,
    GraphPath,
    EvidenceChunk,
    Claim,
    ClassificationLevel,
    ConfidenceLevel
)
from app.services.confidence_service import confidence_service


def test_high_confidence_calculation():
    entities = [
        Entity(id="INC-104", name="Incident 104", type=EntityType.INCIDENT, description="", classification=ClassificationLevel.INTERNAL)
    ]
    paths = [
        GraphPath(path_nodes=["PRJ-GAMMA", "SYS-CNC-07", "INC-104"], path_relationships=["DEPENDS_ON", "AFFECTED_BY"], description="", length=2, score=0.5)
    ]
    evidence = [
        EvidenceChunk(id="EVID-017-01", doc_id="SOP-017", doc_title="SOP", doc_type="SOP", excerpt="", classification=ClassificationLevel.INTERNAL, relevance_score=0.9),
        EvidenceChunk(id="EVID-031-01", doc_id="DOC-031", doc_title="Spec", doc_type="Spec", excerpt="", classification=ClassificationLevel.INTERNAL, relevance_score=0.8),
        EvidenceChunk(id="EVID-055-01", doc_id="DOC-055", doc_title="Manual", doc_type="SOP", excerpt="", classification=ClassificationLevel.INTERNAL, relevance_score=0.7)
    ]
    claims = [
        Claim(text="Shutdown required.", evidence_ids=["EVID-017-01"], is_verified=True),
        Claim(text="Project C affected.", evidence_ids=["EVID-031-01"], is_verified=True)
    ]

    conf = confidence_service.calculate(
        identified_entities=entities,
        graph_paths=paths,
        retrieved_evidence=evidence,
        validated_claims=claims,
        citation_validity_rate=1.0,
        is_insufficient_evidence=False
    )

    assert conf.level == ConfidenceLevel.HIGH
    assert conf.score >= 75.0
    assert conf.breakdown["penalty"] == 0.0


def test_unsupported_claim_penalty_deduction():
    entities = [Entity(id="E1", name="E1", type=EntityType.SYSTEM, description="", classification=ClassificationLevel.INTERNAL)]
    paths = [GraphPath(path_nodes=["A", "B"], path_relationships=["R"], description="", length=1, score=1.0)]
    evidence = [EvidenceChunk(id="EV1", doc_id="D1", doc_title="D", doc_type="SOP", excerpt="", classification=ClassificationLevel.INTERNAL, relevance_score=0.9)]
    
    # 2 unsupported claims
    claims = [
        Claim(text="Claim 1", evidence_ids=[], is_verified=False),
        Claim(text="Claim 2", evidence_ids=["FAKE"], is_verified=False)
    ]

    conf = confidence_service.calculate(
        identified_entities=entities,
        graph_paths=paths,
        retrieved_evidence=evidence,
        validated_claims=claims,
        citation_validity_rate=0.0,
        is_insufficient_evidence=False
    )

    assert conf.breakdown["penalty"] == 30.0  # 2 * 15.0 pts
    assert conf.level == ConfidenceLevel.LOW
