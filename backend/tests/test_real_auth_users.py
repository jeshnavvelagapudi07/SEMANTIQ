"""
Tests for Real Multi-Employee Identity, Salted Password Validation,
Admin Provisioning, Role/Clearance Modification, and Account Revocation.

These tests use the SEED_*_PASSWORD environment variables configured in the test .env.
Configure the following env vars before running (values must match what was used to seed the DB):
  SEED_ADMIN_PASSWORD=<your-admin-password>
  SEED_OPERATIONS_PASSWORD=<your-operations-password>
  SEED_PROJECT_MANAGER_PASSWORD=<your-pm-password>
  SEED_VIEWER_PASSWORD=<your-viewer-password>
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token


def _get_seed_password(env_var: str) -> str:
    """Reads a seed password from environment. Fails clearly if not set."""
    pwd = os.getenv(env_var, "").strip()
    if not pwd:
        pytest.skip(f"{env_var} is not set — skipping credential test.")
    return pwd


@pytest.mark.asyncio
async def test_email_password_valid_authentication():
    """Kenji Sato authenticates with the configured SEED_OPERATIONS_PASSWORD."""
    ops_pwd = _get_seed_password("SEED_OPERATIONS_PASSWORD")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org",
            "password": ops_pwd
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["email"] == "kenji.sato@semantiq.org"
        assert data["role"] == "operations_engineer"
        assert data["employee_id"] == "EMP-002"
        assert data["clearance_level"] == "CONFIDENTIAL"


@pytest.mark.asyncio
async def test_wrong_password_rejected():
    """Wrong password returns HTTP 401 regardless of valid email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org",
            "password": "WrongPassword999!"
        })
        assert res.status_code == 401
        assert "incorrect password" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unknown_email_rejected():
    """Unknown email returns HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "ghost.user@unknown.com",
            "password": "SomePassword123!"
        })
        assert res.status_code == 401
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_password_rejected():
    """Login without a password is rejected with HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org"
        })
        assert res.status_code == 400
        assert "password" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_invites_new_employee_and_employee_logs_in():
    """Admin creates an employee; employee can authenticate with the provisioned password."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"daiki.tanaka.{uid}@semantiq.org"
    admin_token = create_access_token("aris.thorne@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invite_payload = {
            "email": test_email,
            "display_name": "Daiki Tanaka",
            "department": "Thermal Systems Engineering",
            "job_title": "Senior Cryogenic Specialist",
            "role": "operations_engineer",
            "clearance_level": "CONFIDENTIAL",
            "initial_password": "CryoSecure2026!"
        }
        invite_res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invite_payload
        )
        assert invite_res.status_code == 200
        new_user = invite_res.json()["user"]
        assert new_user["email"] == test_email
        assert new_user["role"] == "operations_engineer"
        assert new_user["status"] == "ACTIVE"

        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": "CryoSecure2026!"
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert data["display_name"] == "Daiki Tanaka"
        assert "token" in data


@pytest.mark.asyncio
async def test_non_admin_cannot_invite_employees():
    """Operations engineer cannot create new employees — 403."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    ops_token = create_access_token("kenji.sato@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "email": f"hacker.hire.{uid}@semantiq.org",
                "display_name": "Hacker Hire",
                "department": "Security",
                "job_title": "Intruder",
                "role": "admin",
                "clearance_level": "RESTRICTED",
                "initial_password": "Password123!"
            }
        )
        assert res.status_code == 403
        assert "administrative privileges required" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_modifies_role_and_clearance_with_audit():
    """Admin can promote a user's role and clearance; changes appear in audit ledger."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"promo.user.{uid}@semantiq.org"
    admin_token = create_access_token("aris.thorne@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invite_res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": test_email,
                "display_name": "Promo User",
                "department": "Delivery",
                "job_title": "Associate PM",
                "role": "viewer",
                "clearance_level": "INTERNAL",
                "initial_password": "InitialPass123!"
            }
        )
        assert invite_res.status_code == 200
        u_id = invite_res.json()["user"]["id"]

        role_res = await client.patch(
            f"/api/admin/users/{u_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "project_manager", "reason": "Promoted to full PM"}
        )
        assert role_res.status_code == 200
        assert role_res.json()["user"]["role"] == "project_manager"

        clr_res = await client.patch(
            f"/api/admin/users/{u_id}/clearance",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"clearance_level": "CONFIDENTIAL", "reason": "Granted Level 3 Confidential"}
        )
        assert clr_res.status_code == 200
        assert clr_res.json()["user"]["clearance_level"] == "CONFIDENTIAL"

        audit_res = await client.get(
            "/api/knowledge/changes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert audit_res.status_code == 200
        changes = audit_res.json()["changes"]
        action_types = [c["action_type"] for c in changes]
        assert "USER_ROLE_CHANGE" in action_types
        assert "USER_CLEARANCE_CHANGE" in action_types


@pytest.mark.asyncio
async def test_disabled_account_cannot_authenticate():
    """Disabled accounts are rejected with HTTP 403 even with correct credentials."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"term.user.{uid}@semantiq.org"
    admin_token = create_access_token("aris.thorne@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invite_res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": test_email,
                "display_name": "Terminated User",
                "department": "Contracting",
                "job_title": "Temporary Contractor",
                "role": "viewer",
                "clearance_level": "INTERNAL",
                "initial_password": "TempPassword123!"
            }
        )
        assert invite_res.status_code == 200
        u_id = invite_res.json()["user"]["id"]

        status_res = await client.patch(
            f"/api/admin/users/{u_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "DISABLED", "reason": "Contract ended"}
        )
        assert status_res.status_code == 200
        assert status_res.json()["user"]["status"] == "DISABLED"

        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": "TempPassword123!"
        })
        assert login_res.status_code == 403
        assert "disabled" in login_res.json()["detail"].lower()
