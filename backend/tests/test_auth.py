"""
Unit and Integration Tests for Server-Side Authentication & Session Management
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token, verify_access_token, DEMO_USERS_ROSTER
from app.models.schemas import UserRole
from fastapi import HTTPException


def _ops_password() -> str:
    pwd = os.getenv("SEED_OPERATIONS_PASSWORD", "").strip()
    if not pwd:
        pytest.skip("SEED_OPERATIONS_PASSWORD not set — skipping credential test.")
    return pwd


def _admin_password() -> str:
    pwd = os.getenv("SEED_ADMIN_PASSWORD", "").strip()
    if not pwd:
        pytest.skip("SEED_ADMIN_PASSWORD not set — skipping credential test.")
    return pwd


@pytest.mark.asyncio
async def test_valid_login_returns_signed_token():
    """Email+password login returns a valid signed token."""
    ops_pwd = _ops_password()
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
        assert data["user_id"] == "usr_ops_01"


@pytest.mark.asyncio
async def test_login_without_password_rejected():
    """Login with no password field returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "kenji.sato@semantiq.org"
        })
        assert res.status_code == 400
        assert "password" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_email_rejected():
    """Unknown email returns HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "non_existent_hacker@fake.com",
            "password": "SomePass123!"
        })
        assert res.status_code == 401
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_with_valid_token():
    """Valid token resolves to correct user profile from database."""
    token = create_access_token("aris.thorne@semantiq.org")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "admin_01"
        assert data["role"] == "admin"
        assert data["user_id"] == "usr_admin_01"


@pytest.mark.asyncio
async def test_auth_me_with_tampered_token():
    """Tampered token signature is rejected with 401."""
    token = create_access_token("marcus.vance@semantiq.org")
    tampered_token = token[:-4] + "XXXX"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 401
        assert "signature" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_with_expired_token():
    """Expired token is rejected with 401."""
    token = create_access_token("kenji.sato@semantiq.org", expires_in_seconds=-10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_benchmark_users_directory():
    """GET /auth/users returns the four benchmark accounts without passwords."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/users")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == len(DEMO_USERS_ROSTER)
        roles = [u["role"] for u in data["users"]]
        assert "admin" in roles
        assert "operations_engineer" in roles
        assert "project_manager" in roles
        assert "viewer" in roles
        # Verify no passwords are exposed in the response
        for user in data["users"]:
            assert "password" not in user
            assert "password_hash" not in user
            assert "salt" not in user
