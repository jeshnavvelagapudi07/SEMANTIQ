"""
Tests for Real Multi-Employee Identity, Salted Password Validation,
Admin Provisioning, Role/Clearance Modification, and Account Revocation
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token

@pytest.mark.asyncio
async def test_email_password_valid_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Kenji Sato with valid password
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org",
            "password": "Password123!"
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["email"] == "kenji.sato@semantiq.org"
        assert data["role"] == "operations_engineer"
        assert data["employee_id"] == "EMP-001"
        assert data["clearance_level"] == "CONFIDENTIAL"


@pytest.mark.asyncio
async def test_wrong_password_rejected():
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "ghost.user@unknown.com",
            "password": "SomePassword123!"
        })
        assert res.status_code == 401
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_invites_new_employee_and_employee_logs_in():
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"daiki.tanaka.{uid}@semantiq.org"
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin provisions new employee
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

        # 2. New employee logs in with their credentials
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
    import uuid
    uid = uuid.uuid4().hex[:6]
    ops_token = create_access_token("ops_eng_01")
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
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"promo.user.{uid}@semantiq.org"
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First invite a temporary test user
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

        # 1. Update role to project_manager
        role_res = await client.patch(
            f"/api/admin/users/{u_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "project_manager", "reason": "Promoted to full PM"}
        )
        assert role_res.status_code == 200
        assert role_res.json()["user"]["role"] == "project_manager"

        # 2. Update clearance to CONFIDENTIAL
        clr_res = await client.patch(
            f"/api/admin/users/{u_id}/clearance",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"clearance_level": "CONFIDENTIAL", "reason": "Granted Level 3 Confidential"}
        )
        assert clr_res.status_code == 200
        assert clr_res.json()["user"]["clearance_level"] == "CONFIDENTIAL"

        # 3. Check change audit ledger
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
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"term.user.{uid}@semantiq.org"
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an employee to disable
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

        # Admin disables account
        status_res = await client.patch(
            f"/api/admin/users/{u_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "DISABLED", "reason": "Contract ended"}
        )
        assert status_res.status_code == 200
        assert status_res.json()["user"]["status"] == "DISABLED"

        # Attempt login with valid password -> must be rejected with 403
        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": "TempPassword123!"
        })
        assert login_res.status_code == 403
        assert "disabled" in login_res.json()["detail"].lower()
