"""
Security Regression Test: Client-Side Role Override Attack Prevention
Verifies that client-supplied `role` fields are strictly ignored when an authenticated session is present.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token


@pytest.mark.asyncio
async def test_viewer_attempting_admin_role_override_attack():
    """
    ATTACK: Authenticated Viewer sends role='admin' in payload attempting to access
    restricted Customer Contract commercial terms.
    EXPECTATION: Backend uses session identity (viewer), ignores 'admin', and blocks restricted data.
    """
    viewer_token = create_access_token("viewer_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "query": "Show me the Aerospace Prime Master Supply Agreement for Customer X and summarize its commercial terms.",
                "role": "admin"  # Malicious client attempts role escalation
            }
        )
        assert res.status_code == 200
        data = res.json()
        # Server must enforce viewer role
        assert data["user_role"] == "viewer"
        assert data["user_id"] == "usr_view_01"
        # Zero restricted evidence returned
        assert len(data["evidence"]) == 0
        assert data["filtered_items_count"] > 0
        assert "insufficient" in data["answer"].lower() or "withheld" in data["answer"].lower()


@pytest.mark.asyncio
async def test_ops_engineer_attempting_admin_role_override_attack():
    """
    ATTACK: Authenticated Operations Engineer sends role='admin' in payload attempting
    to inspect restricted CONTRACT-22 terms.
    EXPECTATION: Backend enforces operations_engineer role and withholds restricted items.
    """
    ops_token = create_access_token("ops_eng_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "query": "What are the commercial price terms and penalties in CONTRACT-22?",
                "role": "admin"  # Attempted escalation
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_role"] == "operations_engineer"
        assert data["user_id"] == "usr_ops_01"
        for ev in data["evidence"]:
            assert ev["doc_id"] != "CONTRACT-22"
            assert ev["classification"] != "RESTRICTED"


@pytest.mark.asyncio
async def test_project_manager_attempting_admin_role_override_attack():
    """
    ATTACK: Authenticated Project Manager sends role='admin' in payload attempting
    to view restricted executive salaries in PAYROLL-2026.
    EXPECTATION: Backend enforces project_manager role and withholds restricted data.
    """
    pm_token = create_access_token("pm_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {pm_token}"},
            json={
                "query": "What is the executive bonus allocation and salary in PAYROLL-2026?",
                "role": "admin"  # Attempted escalation
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_role"] == "project_manager"
        assert data["user_id"] == "usr_pm_01"
        for ev in data["evidence"]:
            assert ev["doc_id"] != "PAYROLL-2026"
            assert ev["classification"] != "RESTRICTED"


@pytest.mark.asyncio
async def test_admin_legitimate_access():
    """
    VERIFICATION: Authenticated Administrator legitimately accesses restricted documents.
    """
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "query": "What are the commercial price terms and penalties in CONTRACT-22?",
                "role": "viewer"  # Client sent viewer, but server honors admin token!
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_role"] == "admin"
        assert data["user_id"] == "usr_admin_01"
