"""
Critical Security Boundary & Zero-Leakage Tests
Proves that the permission gate strictly isolates unauthorized data BEFORE LLM context construction.
"""
import pytest
from app.models.schemas import UserRole, ClassificationLevel
from app.services.retrieval_service import retrieval_service
from app.services.permission_service import permission_service
from app.services.graph_service import graph_service
from app.services.llm_service import build_minimized_context


def test_restricted_documents_never_reach_llm_context():
    # Simulate a Viewer querying about restricted Customer Contract terms
    query = "What are the commercial price terms and penalties in CONTRACT-22?"
    role = UserRole.VIEWER

    # Step 1: Entity identification & pre-filtering
    auth_entities, filtered_entities = retrieval_service.identify_entities(query, role)
    auth_ids = [e.id for e in auth_entities]

    # CONTRACT-22 is RESTRICTED and MUST NOT be in authorized entities
    assert "CONTRACT-22" not in auth_ids

    # Step 2: Evidence retrieval
    evidence, filtered_ev = retrieval_service.retrieve_evidence(
        query, role, [], auth_entities, top_k=5
    )

    # Verify no restricted evidence chunk was retrieved
    for ev in evidence:
        assert ev.classification != ClassificationLevel.RESTRICTED
        assert ev.doc_id != "CONTRACT-22"

    # Step 3: Verify context payload construction
    context = build_minimized_context(query, role, auth_entities, [], evidence)

    # Critical Assertion: Zero occurrence of restricted contract content in authorized context data
    assert not any(e["id"] == "CONTRACT-22" for e in context["authorized_entities"])
    assert not any(ev["doc_id"] == "CONTRACT-22" for ev in context["authorized_evidence"])
    assert "42,500" not in str(context["authorized_evidence"])
    assert "liquidated damages" not in str(context["authorized_evidence"]).lower()
    assert "trade secrets" not in str(context["authorized_evidence"]).lower()


def test_unauthorized_user_cannot_access_confidential_systems():
    # Viewer tries to access SCADA Engine 01 (CONFIDENTIAL)
    viewer_subgraph = graph_service.get_authorized_subgraph(UserRole.VIEWER)
    assert "SYS-SCADA-01" not in viewer_subgraph

    # Even if direct path lookup is attempted, path search returns empty
    paths = graph_service.find_paths_between("PRJ-THETA", "SYS-SCADA-01", UserRole.VIEWER)
    assert len(paths) == 0


def test_permission_layer_preempts_llm():
    # Ensure permission filtering does not rely on LLM outputs
    # Directly filter documents
    all_docs = retrieval_service.documents
    auth_docs, filtered_docs = permission_service.filter_documents(UserRole.VIEWER, all_docs)
    
    restricted_found_in_auth = any(d.classification == ClassificationLevel.RESTRICTED for d in auth_docs)
    assert restricted_found_in_auth is False
    assert len(filtered_docs) >= 2  # CONTRACT-22 and PAYROLL-2026 filtered
