"""
End-to-End Pipeline Integration Tests
Validates complete query executions, killer demos, action approvals, and evaluation endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
from app.services.graph_service import graph_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_app_state():
    graph_service.load_data(SEED_ENTITIES, SEED_RELATIONSHIPS)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["knowledge_graph"]["nodes"] > 20


def test_killer_demo_1_incident_104_reasoning():
    payload = {
        "query": "Which projects are affected by Incident 104 and what should the responsible team do?",
        "role": "operations_engineer",
        "user_id": "usr_ops_01",
        "max_hops": 3
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify identified entities & paths
    assert len(data["reasoning_trace"]["authorized_entities"]) > 0
    assert len(data["graph_paths"]) > 0

    # Verify grounded claims and validated citations
    assert len(data["claims"]) > 0
    assert all(c["is_verified"] for c in data["claims"])

    # Verify confidence
    assert data["confidence"]["score"] >= 75.0

    # Verify human approval action was created
    assert data["requires_human_review"] is True
    assert data["action_item"] is not None
    assert data["action_item"]["status"] == "PENDING"


def test_killer_demo_2_project_c_high_risk():
    payload = {
        "query": "Why is Project C considered high risk?",
        "role": "operations_engineer",
        "user_id": "usr_ops_01",
        "max_hops": 3
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "Project C" in data["answer"] or "PRJ-GAMMA" in data["answer"]
    assert len(data["graph_paths"]) > 0
    assert data["confidence"]["level"] in ["HIGH", "MEDIUM"]


def test_security_demo_viewer_restricted_contract():
    payload = {
        "query": "What are the commercial contract terms and pricing for Customer X?",
        "role": "viewer",  # Viewer lacks clearance
        "user_id": "usr_viewer_01"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must flag insufficient evidence or safe refusal
    assert data["is_insufficient_evidence"] is True or "Insufficient" in data["answer"]
    # Verify no restricted evidence chunk reached the response
    for ev in data["evidence"]:
        assert ev["classification"] != "RESTRICTED"


def test_action_approval_workflow():
    # First create a query that generates an action
    payload = {
        "query": "Which projects are affected by Incident 104 and what should the responsible team do?",
        "role": "operations_engineer"
    }
    res = client.post("/api/query", json=payload)
    data = res.json()
    action = data.get("action_item")
    assert action is not None
    action_id = action["id"]

    # Approve action
    app_res = client.post(f"/api/actions/{action_id}/approve", json={"user_id": "usr_lead_01", "comment": "Verified and approved."})
    assert app_res.status_code == 200
    updated = app_res.json()
    assert updated["status"] == "APPROVED"
    assert updated["reviewed_by"] == "usr_lead_01"


def test_evaluation_endpoint():
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    report = response.json()

    assert report["total_tests"] >= 10
    assert report["pass_rate"] >= 80.0
    assert report["permission_violation_rate"] == 0.0
    assert report["unsupported_claim_rate"] == 0.0
