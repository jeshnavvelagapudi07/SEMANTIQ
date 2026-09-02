"""
Unit and Integration Tests for Server-Side Authentication & Session Management
"""
import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token, verify_access_token, DEMO_USERS
from app.models.schemas import UserRole
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_valid_login_returns_signed_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={"username": "ops_eng_01"})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["username"] == "ops_eng_01"
        assert data["role"] == "operations_engineer"
        assert data["user_id"] == "usr_ops_01"


@pytest.mark.asyncio
async def test_invalid_login_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={"username": "non_existent_hacker"})
        assert res.status_code == 401
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_with_valid_token():
    token = create_access_token("admin_01")
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
    token = create_access_token("viewer_01")
    # Tamper with signature
    tampered_token = token[:-4] + "XXXX"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 401
        assert "signature" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_with_expired_token():
    # Create token with -10 second expiration
    token = create_access_token("ops_eng_01", expires_in_seconds=-10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_demo_users_directory():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/users")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == len(DEMO_USERS)
        roles = [u["role"] for u in data["users"]]
        assert "admin" in roles
        assert "operations_engineer" in roles
        assert "project_manager" in roles
        assert "viewer" in roles
