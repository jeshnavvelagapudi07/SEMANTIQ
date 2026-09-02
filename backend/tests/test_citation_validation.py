"""
Unit Tests for Citation Validation Service
Validates strict citation checks, rejecting fake evidence IDs and unauthorized citations.
"""
import pytest
from app.models.schemas import Claim, EvidenceChunk, ClassificationLevel, UserRole
from app.services.validation_service import validation_service


def test_valid_citation_matching():
    retrieved_ev = [
        EvidenceChunk(
            id="EVID-017-01",
            doc_id="SOP-017",
            doc_title="CNC SOP",
            doc_type="SOP",
            excerpt="Shutdown required over 68C",
            classification=ClassificationLevel.INTERNAL,
            relevance_score=0.9
        )
    ]

    claims = [
        Claim(text="CNC spindle must be halted when over 68C.", evidence_ids=["EVID-017-01"])
    ]

    validated_claims, status, checks, rate = validation_service.validate_citations(
        claims, retrieved_ev, UserRole.OPERATIONS_ENGINEER
    )

    assert status == "PASSED"
    assert rate == 1.0
    assert validated_claims[0].is_verified is True
    assert validated_claims[0].unsupported_reason is None


def test_fake_hallucinated_citation_rejected():
    retrieved_ev = [
        EvidenceChunk(
            id="EVID-017-01",
            doc_id="SOP-017",
            doc_title="CNC SOP",
            doc_type="SOP",
            excerpt="Shutdown required over 68C",
            classification=ClassificationLevel.INTERNAL,
            relevance_score=0.9
        )
    ]

    claims = [
        Claim(text="Machine must be replaced immediately.", evidence_ids=["EVID-FAKE-999"])
    ]

    validated_claims, status, checks, rate = validation_service.validate_citations(
        claims, retrieved_ev, UserRole.OPERATIONS_ENGINEER
    )

    assert status == "FAILED"
    assert rate == 0.0
    assert validated_claims[0].is_verified is False
    assert "was not in retrieved context" in validated_claims[0].unsupported_reason


def test_unauthorized_citation_rejected():
    # Restricted evidence chunk
    restricted_ev = [
        EvidenceChunk(
            id="EVID-CTR22-01",
            doc_id="CONTRACT-22",
            doc_title="Customer Contract",
            doc_type="Contract",
            excerpt="Price is $42,500",
            classification=ClassificationLevel.RESTRICTED,
            relevance_score=0.9
        )
    ]

    claims = [
        Claim(text="Contract price is $42,500 per unit.", evidence_ids=["EVID-CTR22-01"])
    ]

    # Operations Engineer does not have clearance for RESTRICTED
    validated_claims, status, checks, rate = validation_service.validate_citations(
        claims, restricted_ev, UserRole.OPERATIONS_ENGINEER
    )

    assert status == "FAILED"
    assert validated_claims[0].is_verified is False
    assert "requires higher clearance" in validated_claims[0].unsupported_reason
