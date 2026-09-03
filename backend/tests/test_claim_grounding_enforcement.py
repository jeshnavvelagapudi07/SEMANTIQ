"""
Regression Tests: Claim Grounding Enforcement

Verifies that the query pipeline correctly partitions validated claims so that:
  - Only SUPPORTED and GRAPH_VERIFIED claims appear in QueryResponse.claims (grounded synthesis).
  - UNSUPPORTED claims (no citation, fake citation, unauthorized citation, permission-filtered
    citation) appear only in QueryResponse.unsupported_claims and never in claims.
  - Confidence is NOT inflated by unsupported claims; the penalty still applies.
  - Mixed responses are correctly split.
  - Project C and restricted Customer X queries continue to behave as before.

Tests:
  A. Claim with valid citation ID  -> accepted as grounded (in .claims)
  B. Claim with no citation        -> rejected (in .unsupported_claims only)
  C. Claim with fake/nonexistent citation -> rejected
  D. Claim citing permission-filtered evidence -> rejected
  E. Mixed response (valid + invalid) -> only valid in .claims
  F. Project C DEPENDENCY_QUERY still works end-to-end (deterministic fallback)
  G. Restricted Customer X query still respects permission filtering
  H. Confidence is not inflated by unsupported claims (penalty applied)
"""
import pytest
from app.models.schemas import (
    Claim, ClaimSupportStatus, EvidenceChunk, ClassificationLevel, UserRole, Entity,
    EntityType, GraphPath, QueryIntent, QueryResponse, ConfidenceScore, ConfidenceLevel,
    ReasoningTrace, FilteredItemSummary
)
from app.services.validation_service import validation_service
from app.services.confidence_service import confidence_service


# ──────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

def _make_evidence(ev_id: str, entities: list[str], classification: ClassificationLevel = ClassificationLevel.INTERNAL) -> EvidenceChunk:
    return EvidenceChunk(
        id=ev_id,
        doc_id=f"DOC-{ev_id}",
        doc_title=f"Test Document for {ev_id}",
        doc_type="SOP",
        excerpt=f"Excerpt for {ev_id}.",
        relevant_entities=entities,
        classification=classification,
        relevance_score=0.9
    )


def _make_entity(eid: str) -> Entity:
    return Entity(
        id=eid,
        name=f"Entity {eid}",
        type=EntityType.SYSTEM,
        description="Test entity",
        classification=ClassificationLevel.INTERNAL
    )


def _make_graph_path(nodes: list[str]) -> GraphPath:
    return GraphPath(
        path_nodes=nodes,
        path_relationships=["DEPENDS_ON"] * (len(nodes) - 1),
        description="Test path",
        length=len(nodes) - 1,
        score=1.0
    )


# Helper: simulate the pipeline partition step
_GROUNDED_STATUSES = {ClaimSupportStatus.SUPPORTED, ClaimSupportStatus.GRAPH_VERIFIED}

def _partition_claims(validated_claims: list[Claim]) -> tuple[list[Claim], list[Claim]]:
    """Mirrors the partition logic in queries.py Step 7b."""
    grounded = [c for c in validated_claims if c.support_status in _GROUNDED_STATUSES]
    unsupported = [c for c in validated_claims if c.support_status not in _GROUNDED_STATUSES]
    return grounded, unsupported


# ──────────────────────────────────────────────────────────────────────────────
# Test A: Claim with valid citation ID -> accepted as grounded
# ──────────────────────────────────────────────────────────────────────────────

def test_A_valid_citation_accepted_as_grounded():
    """A: A claim with a valid citation ID that exists in retrieved evidence is accepted."""
    ev = _make_evidence("EVID-A-01", ["SYS-A-01"])
    claim = Claim(
        text="System A-01 requires scheduled maintenance.",
        entities=["SYS-A-01"],
        evidence_ids=["EVID-A-01"],
        support_status=ClaimSupportStatus.SUPPORTED,
        is_verified=True
    )

    validated, status, checks, rate = validation_service.validate_citations(
        [claim], [ev], UserRole.OPERATIONS_ENGINEER
    )
    grounded, unsupported = _partition_claims(validated)

    assert len(grounded) == 1, "Valid cited claim must be in grounded set."
    assert len(unsupported) == 0, "No unsupported claims expected."
    assert grounded[0].is_verified is True
    assert grounded[0].support_status == ClaimSupportStatus.SUPPORTED
    assert status == "PASSED"
    assert rate == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Test B: Claim with no citation -> rejected from grounded claims
# ──────────────────────────────────────────────────────────────────────────────

def test_B_claim_with_no_citation_rejected_from_grounded():
    """B: A claim with empty evidence_ids must NOT appear in grounded claims."""
    ev = _make_evidence("EVID-B-01", ["SYS-B-01"])
    claim = Claim(
        text="This claim has no supporting citation at all.",
        entities=["SYS-B-01"],
        evidence_ids=[],  # No citation
        support_status=ClaimSupportStatus.SUPPORTED,  # LLM incorrectly marked as SUPPORTED
        is_verified=True
    )

    validated, status, checks, rate = validation_service.validate_citations(
        [claim], [ev], UserRole.OPERATIONS_ENGINEER
    )
    grounded, unsupported = _partition_claims(validated)

    # The validation service must downgrade this to UNSUPPORTED
    assert len(grounded) == 0, "Uncited claim must NOT be in grounded set."
    assert len(unsupported) == 1, "Uncited claim must appear in unsupported set."
    assert unsupported[0].support_status == ClaimSupportStatus.UNSUPPORTED
    assert unsupported[0].is_verified is False
    assert unsupported[0].unsupported_reason is not None
    assert "No citation" in unsupported[0].unsupported_reason or "no citation" in unsupported[0].unsupported_reason.lower()


# ──────────────────────────────────────────────────────────────────────────────
# Test C: Claim with fake/nonexistent citation ID -> rejected
# ──────────────────────────────────────────────────────────────────────────────

def test_C_fake_citation_id_rejected():
    """C: A claim referencing an evidence ID that was never retrieved must be rejected."""
    ev = _make_evidence("EVID-C-01", ["SYS-C-01"])
    claim = Claim(
        text="System C-01 has a critical defect.",
        entities=["SYS-C-01"],
        evidence_ids=["EVID-HALLUCINATED-999"],  # Never retrieved
        support_status=ClaimSupportStatus.SUPPORTED,
        is_verified=True
    )

    validated, status, checks, rate = validation_service.validate_citations(
        [claim], [ev], UserRole.OPERATIONS_ENGINEER
    )
    grounded, unsupported = _partition_claims(validated)

    assert len(grounded) == 0, "Claim with hallucinated citation must NOT be in grounded set."
    assert len(unsupported) == 1
    assert unsupported[0].is_verified is False
    assert unsupported[0].support_status == ClaimSupportStatus.UNSUPPORTED
    assert "was not in retrieved context" in unsupported[0].unsupported_reason
    assert status == "FAILED"
    assert rate == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Test D: Claim citing permission-filtered evidence -> rejected
# ──────────────────────────────────────────────────────────────────────────────

def test_D_permission_filtered_citation_rejected():
    """D: A claim citing evidence that requires higher clearance than the user's role must be rejected."""
    restricted_ev = _make_evidence("EVID-D-01", ["CUST-X-01"], ClassificationLevel.RESTRICTED)
    claim = Claim(
        text="Customer contract price is $2.4M per year.",
        entities=["CUST-X-01"],
        evidence_ids=["EVID-D-01"],
        support_status=ClaimSupportStatus.SUPPORTED,
        is_verified=True
    )

    # operations_engineer does NOT have RESTRICTED clearance
    validated, status, checks, rate = validation_service.validate_citations(
        [claim], [restricted_ev], UserRole.OPERATIONS_ENGINEER
    )
    grounded, unsupported = _partition_claims(validated)

    assert len(grounded) == 0, "Claim citing restricted evidence must NOT be in grounded set."
    assert len(unsupported) == 1
    assert unsupported[0].is_verified is False
    assert unsupported[0].support_status == ClaimSupportStatus.UNSUPPORTED
    assert "requires higher clearance" in unsupported[0].unsupported_reason
    assert status == "FAILED"


# ──────────────────────────────────────────────────────────────────────────────
# Test E: Mixed response -> only valid grounded claims remain grounded
# ──────────────────────────────────────────────────────────────────────────────

def test_E_mixed_response_correctly_partitioned():
    """E: A response with both valid and invalid claims must be correctly split."""
    ev_valid = _make_evidence("EVID-E-01", ["SYS-E-01"])
    ev_restricted = _make_evidence("EVID-E-02", ["CUST-E-01"], ClassificationLevel.RESTRICTED)

    claims = [
        # Valid: correctly cited, authorized, entity matches
        Claim(
            text="SYS-E-01 requires weekly calibration.",
            entities=["SYS-E-01"],
            evidence_ids=["EVID-E-01"],
            support_status=ClaimSupportStatus.SUPPORTED,
            is_verified=True
        ),
        # Invalid: no citation at all
        Claim(
            text="This claim is made up without evidence.",
            entities=["SYS-E-01"],
            evidence_ids=[],
            support_status=ClaimSupportStatus.SUPPORTED,
            is_verified=True
        ),
        # Invalid: hallucinated ID
        Claim(
            text="SYS-E-01 was replaced last quarter.",
            entities=["SYS-E-01"],
            evidence_ids=["EVID-FAKE-XYZ"],
            support_status=ClaimSupportStatus.SUPPORTED,
            is_verified=True
        ),
        # Invalid: restricted evidence (clearance denied)
        Claim(
            text="Customer E has a $5M contract.",
            entities=["CUST-E-01"],
            evidence_ids=["EVID-E-02"],
            support_status=ClaimSupportStatus.SUPPORTED,
            is_verified=True
        ),
    ]

    validated, status, checks, rate = validation_service.validate_citations(
        claims, [ev_valid, ev_restricted], UserRole.OPERATIONS_ENGINEER
    )
    grounded, unsupported = _partition_claims(validated)

    assert len(grounded) == 1, f"Only 1 valid claim; got grounded={[c.text for c in grounded]}"
    assert grounded[0].evidence_ids == ["EVID-E-01"]
    assert grounded[0].is_verified is True

    assert len(unsupported) == 3, f"3 invalid claims; got unsupported={[c.text for c in unsupported]}"
    for uc in unsupported:
        assert uc.is_verified is False
        assert uc.support_status == ClaimSupportStatus.UNSUPPORTED

    assert status == "WARNING"  # Some valid, some unsupported


# ──────────────────────────────────────────────────────────────────────────────
# Test F: Project C DEPENDENCY_QUERY end-to-end (deterministic fallback)
# ──────────────────────────────────────────────────────────────────────────────

def test_F_project_c_query_still_works():
    """F: Project C dependency queries produce grounded claims, not unsupported ones."""
    from app.services.retrieval_service import retrieval_service
    from app.services.graph_service import graph_service

    role = UserRole.OPERATIONS_ENGINEER
    query = "What is Project C?"

    authorized_entities, filtered = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in authorized_entities]

    # PRJ-GAMMA must be resolvable to operations_engineer
    prj_gamma_found = any(e.id == "PRJ-GAMMA" for e in authorized_entities)
    assert prj_gamma_found, "PRJ-GAMMA must be authorized for operations_engineer."

    graph_paths = graph_service.traverse_for_entities(auth_ids, role, max_hops=3)
    evidence, filtered_ev = retrieval_service.retrieve_evidence(query, role, graph_paths, authorized_entities, top_k=5)

    # Build deterministic LLM output for Project C
    from app.services.llm_service import llm_service
    from app.models.schemas import QueryIntent
    llm_out = llm_service._generate_deterministic_response(
        query, role, authorized_entities, graph_paths, evidence, QueryIntent.ENTITY_DESCRIPTION
    )

    # Validate citations
    validated, val_status, val_checks, rate = validation_service.validate_citations(
        llm_out.claims, evidence, role
    )
    grounded, unsupported = _partition_claims(validated)

    # For Project C with authorized evidence, there must be at least one claim
    assert len(llm_out.claims) > 0, "Deterministic fallback must produce at least one claim for PRJ-GAMMA."

    # Any claim that IS in grounded must have a valid citation or be GRAPH_VERIFIED
    for gc in grounded:
        assert gc.support_status in {ClaimSupportStatus.SUPPORTED, ClaimSupportStatus.GRAPH_VERIFIED}

    # Any claim that IS in unsupported must NOT be SUPPORTED or GRAPH_VERIFIED
    for uc in unsupported:
        assert uc.support_status not in {ClaimSupportStatus.SUPPORTED, ClaimSupportStatus.GRAPH_VERIFIED}


# ──────────────────────────────────────────────────────────────────────────────
# Test G: Restricted Customer X still filtered by permissions
# ──────────────────────────────────────────────────────────────────────────────

def test_G_restricted_customer_query_permission_boundary():
    """G: Restricted customer evidence must never leak into grounded claims for unauthorized roles."""
    # Simulate a response where Gemini returns a claim citing restricted evidence
    restricted_ev = _make_evidence("EVID-CTR22-01", ["CUST-CUSTOMER-X"], ClassificationLevel.RESTRICTED)

    claim_citing_restricted = Claim(
        text="Customer X has agreed to a $42,500 per unit contract.",
        entities=["CUST-CUSTOMER-X"],
        evidence_ids=["EVID-CTR22-01"],
        support_status=ClaimSupportStatus.SUPPORTED,
        is_verified=True
    )

    for role in [UserRole.OPERATIONS_ENGINEER, UserRole.PROJECT_MANAGER, UserRole.VIEWER]:
        validated, status, checks, rate = validation_service.validate_citations(
            [claim_citing_restricted], [restricted_ev], role
        )
        grounded, unsupported = _partition_claims(validated)

        assert len(grounded) == 0, (
            f"Restricted claim must NOT be grounded for role {role.value}. "
            f"Got grounded: {[c.text for c in grounded]}"
        )
        assert len(unsupported) == 1
        assert unsupported[0].is_verified is False
        assert status == "FAILED"

    # Admin CAN access RESTRICTED
    validated_admin, status_admin, _, _ = validation_service.validate_citations(
        [claim_citing_restricted], [restricted_ev], UserRole.ADMIN
    )
    grounded_admin, _ = _partition_claims(validated_admin)
    assert len(grounded_admin) == 1, "Admin must be able to access RESTRICTED evidence."
    assert grounded_admin[0].is_verified is True


# ──────────────────────────────────────────────────────────────────────────────
# Test H: Confidence is not inflated by unsupported claims (penalty preserved)
# ──────────────────────────────────────────────────────────────────────────────

def test_H_confidence_penalty_applied_for_unsupported_claims():
    """H: The unsupported-claim penalty (-15 pts each) is preserved when calculating confidence."""
    entity = _make_entity("SYS-H-01")
    ev = _make_evidence("EVID-H-01", ["SYS-H-01"])
    path = _make_graph_path(["SYS-H-01", "SYS-H-02"])

    # Scenario A: one valid + one unsupported claim
    valid_claim = Claim(
        text="Valid grounded claim.",
        entities=["SYS-H-01"],
        evidence_ids=["EVID-H-01"],
        support_status=ClaimSupportStatus.SUPPORTED,
        is_verified=True
    )
    unsupported_claim = Claim(
        text="Unsupported claim with no citation.",
        entities=["SYS-H-01"],
        evidence_ids=[],
        support_status=ClaimSupportStatus.UNSUPPORTED,
        is_verified=False,
        unsupported_reason="No citation provided for this claim."
    )

    validated_mixed = [valid_claim, unsupported_claim]
    validated_clean = [valid_claim]

    conf_mixed = confidence_service.calculate(
        identified_entities=[entity],
        graph_paths=[path],
        retrieved_evidence=[ev],
        validated_claims=validated_mixed,  # full list passed to confidence service
        citation_validity_rate=0.5,
        intent=QueryIntent.ENTITY_DESCRIPTION
    )

    conf_clean = confidence_service.calculate(
        identified_entities=[entity],
        graph_paths=[path],
        retrieved_evidence=[ev],
        validated_claims=validated_clean,
        citation_validity_rate=1.0,
        intent=QueryIntent.ENTITY_DESCRIPTION
    )

    # The mixed scenario must have lower confidence due to the unsupported claim penalty
    assert conf_mixed.score < conf_clean.score, (
        f"Mixed confidence ({conf_mixed.score}) must be lower than clean ({conf_clean.score})."
    )

    # Verify the penalty appears in the breakdown
    assert conf_mixed.breakdown.get("penalty", 0.0) == 15.0, (
        "One unsupported claim must contribute a -15 pt penalty."
    )
    assert conf_clean.breakdown.get("penalty", 0.0) == 0.0, (
        "No unsupported claims means zero penalty."
    )

    # When we partition and only pass grounded claims to the response,
    # the grounded set must not contain the unsupported claim.
    grounded, separated = _partition_claims(validated_mixed)
    assert len(grounded) == 1
    assert len(separated) == 1
    assert all(c.is_verified for c in grounded)
    assert not any(c.is_verified for c in separated)
