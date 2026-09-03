"""
Regression Tests: PostgreSQL Persistence & Authentication Lifecycle

Verifies:
1. Employee creation commits to the database and is retrievable via a new DB request.
2. Create -> logout -> authenticate again cycle works end-to-end.
3. Role escalation via client payload is blocked server-side.
4. Admin clearance (EMP-001) is RESTRICTED, operations engineer (EMP-002) is CONFIDENTIAL.
5. Benchmark user employee IDs match the canonical schema (EMP-001 = admin, EMP-002 = ops, etc.).
"""
import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token
from app.services.user_service import user_service
from app.core.database import get_db_connection, hash_password, verify_password


# ──────────────────────────────────────────────────────────────────────────────
# Persistence: Create -> new DB request -> employee exists
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_employee_persists_across_db_requests():
    """
    Creates an employee via the API, then retrieves it with a fresh database
    connection to confirm it was committed to PostgreSQL — not held in memory.
    """
    uid = uuid.uuid4().hex[:6]
    test_email = f"persist.{uid}@semantiq.org"
    admin_token = create_access_token("aris.thorne@semantiq.org")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invite_res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": test_email,
                "display_name": "Persistence Test User",
                "department": "Test Engineering",
                "job_title": "Database Integrity Specialist",
                "role": "viewer",
                "clearance_level": "INTERNAL",
                "initial_password": "Persist2026!Test"
            }
        )
        assert invite_res.status_code == 200, f"Invite failed: {invite_res.text}"
        created_id = invite_res.json()["user"]["id"]

    # Use a NEW database connection — not the same request context
    retrieved = user_service.get_user_by_id(created_id)
    assert retrieved is not None, "Employee must exist in PostgreSQL after creation."
    assert retrieved["email"] == test_email
    assert retrieved["role"] == "viewer"
    assert retrieved["status"] == "ACTIVE"

    # Also confirm retrieval by email via a separate query
    retrieved_by_email = user_service.get_user_by_email_or_username(test_email)
    assert retrieved_by_email is not None
    assert retrieved_by_email["id"] == created_id


@pytest.mark.asyncio
async def test_create_then_authenticate_after_separate_login():
    """
    Create employee -> verify they can authenticate in a separate login call
    (simulates a logout/login cycle against the persistent database).
    """
    uid = uuid.uuid4().hex[:6]
    test_email = f"login.cycle.{uid}@semantiq.org"
    admin_token = create_access_token("aris.thorne@semantiq.org")
    initial_password = "LoginCycle2026!Secure"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Admin creates the employee
        invite_res = await client.post(
            "/api/admin/users/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": test_email,
                "display_name": "Login Cycle User",
                "department": "Authentication Testing",
                "job_title": "Test Analyst",
                "role": "project_manager",
                "clearance_level": "CONFIDENTIAL",
                "initial_password": initial_password
            }
        )
        assert invite_res.status_code == 200

        # Step 2: Authenticate with the provisioned credentials (simulates fresh login)
        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": initial_password
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert data["role"] == "project_manager"
        assert data["clearance_level"] == "CONFIDENTIAL"
        token = data["token"]
        assert len(token) > 0

        # Step 3: Verify /me resolves server-side from the new token
        me_res = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == test_email
        assert me_data["role"] == "project_manager"


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark User Employee IDs & Clearances
# ──────────────────────────────────────────────────────────────────────────────

def test_benchmark_admin_is_emp001_restricted():
    """Dr. Aris Thorne must be EMP-001, role=admin, clearance=RESTRICTED."""
    user = user_service.get_user_by_email_or_username("aris.thorne@semantiq.org")
    assert user is not None
    assert user["employee_id"] == "EMP-001"
    assert user["role"] == "admin"
    assert user["clearance_level"] == "RESTRICTED"


def test_benchmark_operations_engineer_is_emp002_confidential():
    """Kenji Sato must be EMP-002, role=operations_engineer, clearance=CONFIDENTIAL."""
    user = user_service.get_user_by_email_or_username("kenji.sato@semantiq.org")
    assert user is not None
    assert user["employee_id"] == "EMP-002"
    assert user["role"] == "operations_engineer"
    assert user["clearance_level"] == "CONFIDENTIAL"


def test_benchmark_project_manager_is_emp003_confidential():
    """Elena Rostova must be EMP-003, role=project_manager, clearance=CONFIDENTIAL."""
    user = user_service.get_user_by_email_or_username("elena.rostova@semantiq.org")
    assert user is not None
    assert user["employee_id"] == "EMP-003"
    assert user["role"] == "project_manager"
    assert user["clearance_level"] == "CONFIDENTIAL"


def test_benchmark_viewer_is_emp004_internal():
    """Marcus Vance must be EMP-004, role=viewer, clearance=INTERNAL."""
    user = user_service.get_user_by_email_or_username("marcus.vance@semantiq.org")
    assert user is not None
    assert user["employee_id"] == "EMP-004"
    assert user["role"] == "viewer"
    assert user["clearance_level"] == "INTERNAL"


# ──────────────────────────────────────────────────────────────────────────────
# Password Security: hashes stored, not plaintext
# ──────────────────────────────────────────────────────────────────────────────

def test_benchmark_user_passwords_are_hashed_not_plaintext():
    """
    Verifies that none of the benchmark users have a plaintext password stored.
    The password_hash column must be a hex digest, never a recognizable password string.
    """
    emails = [
        "aris.thorne@semantiq.org",
        "kenji.sato@semantiq.org",
        "elena.rostova@semantiq.org",
        "marcus.vance@semantiq.org",
    ]
    forbidden_patterns = [
        "Password123!", "password", "Semantiq", "2026Pg", "admin", "pass"
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        for email in emails:
            cursor.execute(
                "SELECT password_hash, salt FROM users WHERE LOWER(email) = LOWER(%s)",
                (email,)
            )
            row = cursor.fetchone()
            assert row is not None, f"Benchmark user {email} not found."
            h = row["password_hash"]
            s = row["salt"]
            assert len(h) == 64, f"Hash for {email} must be 64-char hex (SHA-256). Got: {len(h)}"
            assert len(s) == 32, f"Salt for {email} must be 32-char hex. Got: {len(s)}"
            for pattern in forbidden_patterns:
                assert pattern.lower() not in h.lower(), (
                    f"Plaintext pattern '{pattern}' found in password_hash for {email}!"
                )


# ──────────────────────────────────────────────────────────────────────────────
# Role Escalation Protection
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_client_supplied_role_in_query_payload_is_ignored():
    """
    Client sends role=admin in the query payload.
    Server must resolve role from the authenticated token — client role is ignored.
    """
    ops_token = create_access_token("kenji.sato@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "query": "What is Project C?",
                "role": "admin",  # Client tries to escalate — must be ignored
                "max_hops": 2
            }
        )
        assert res.status_code == 200
        data = res.json()
        # Server must have used the token-resolved role, not the client-supplied "admin"
        assert data["user_role"] == "operations_engineer", (
            f"Role escalation via payload succeeded — server returned: {data['user_role']}"
        )


@pytest.mark.asyncio
async def test_viewer_cannot_manage_users():
    """Viewer role cannot access admin user management endpoints."""
    viewer_token = create_access_token("marcus.vance@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_no_password_login_rejected():
    """Login endpoint rejects requests without a password (no dev bypass)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org"
            # No password field
        })
        assert res.status_code == 400
        assert "password" in res.json()["detail"].lower()
