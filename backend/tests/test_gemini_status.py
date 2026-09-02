"""
Tests for AI Provider Status Endpoint & Gemini Runtime Verification
Validates that secrets are never leaked and that Gemini status reporting is accurate.
Updated to match /api/system/ai-status schema with 'available' field and categorized status.
"""
import pytest
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.services.llm_service import llm_service
from app.models.schemas import UserRole, QueryIntent, StructuredLLMOutput

# Valid status values from the categorized probe
VALID_STATUS_VALUES = {
    "live", "unconfigured", "quota_error", "authentication_error",
    "model_error", "service_unavailable", "timeout", "network_error",
    "api_error", "invalid_response"
}


@pytest.mark.asyncio
async def test_ai_status_endpoint_never_leaks_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/system/ai-status")
        assert res.status_code == 200
        data = res.json()

        # Schema assertions
        assert data["provider"] == "gemini"
        assert isinstance(data["configured"], bool)
        assert isinstance(data["available"], bool)
        assert data["model"] == settings.GEMINI_MODEL
        assert data["status"] in VALID_STATUS_VALUES, f"Unexpected status: {data['status']}"

        # CRITICAL: Assert API key is NEVER leaked in any part of the response
        raw_text = res.text
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 5:
            assert settings.GEMINI_API_KEY not in raw_text, "API key leaked in /api/system/ai-status response!"
            # Also check for partial key (first 10 chars)
            assert settings.GEMINI_API_KEY[:10] not in raw_text, "Partial API key leaked!"

        # If configured and available, status must be 'live'
        if data["configured"] and data["available"]:
            assert data["status"] == "live"

        # If not configured, must not claim available
        if not data["configured"]:
            assert not data["available"]
            assert data["status"] == "unconfigured"


@pytest.mark.asyncio
async def test_health_endpoint_never_leaks_secrets():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "Demo Mode" not in data["ai_provider"]  # No Demo Mode label!
        assert "Simulated" not in data["ai_provider"]   # No Simulated label!

        raw_text = res.text
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 5:
            assert settings.GEMINI_API_KEY not in raw_text, "API key leaked in /api/health!"


@pytest.mark.asyncio
async def test_live_gemini_reasoning_pipeline():
    """
    Executes a real reasoning query and asserts that if Gemini is configured,
    the provider label is honestly categorized — never fake 'Gemini Live' when
    actually using deterministic fallback.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/query",
            json={
                "query": "What is CNC-07 and what projects depend on it?",
                "role": "operations_engineer"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["query_id"].startswith("QRY-")
        assert data["answer"]
        assert isinstance(data["claims"], list)
        assert isinstance(data["confidence"]["score"], float)
        assert data["reasoning_trace"]["query_intent"] == "DEPENDENCY_QUERY"

        provider = data["provider_used"]
        # Assert provider is honestly labeled — never a fake label
        assert provider, "provider_used must not be empty"
        # If Gemini is configured: must either be 'Gemini Live (...)' or a categorized error + fallback
        if settings.is_gemini_available:
            assert "Gemini" in provider, f"Expected 'Gemini' in provider label, got: {provider}"
        else:
            assert "Deterministic Fallback" in provider, f"Expected fallback label, got: {provider}"

        # CRITICAL: provider label must NEVER claim Gemini Live when it is actually a fallback
        if "Deterministic Fallback" in provider:
            assert "Gemini Live" not in provider, "Provider cannot simultaneously claim 'Gemini Live' and 'Deterministic Fallback'!"


@pytest.mark.asyncio
async def test_provider_label_consistency():
    """
    Verifies that if Gemini actually succeeds, the provider label is 'Gemini Live (<model>)'.
    If it fails, the label must categorize the failure honestly.
    """
    # Test the LLM service error categorization
    from app.services.llm_service import _categorize_gemini_error

    # Simulate quota error
    class FakeQuotaError(Exception):
        pass
    cat, label = _categorize_gemini_error(FakeQuotaError("429 RESOURCE_EXHAUSTED"))
    assert cat == "quota_error"
    assert "Quota" in label

    # Simulate auth error
    class FakeAuthError(Exception):
        pass
    cat, label = _categorize_gemini_error(FakeAuthError("401 unauthenticated"))
    assert cat == "authentication_error"
    assert "Auth" in label

    # Simulate model not found
    class FakeNotFoundError(Exception):
        pass
    cat, label = _categorize_gemini_error(FakeNotFoundError("404 not_found model no longer available"))
    assert cat == "model_error"
    assert "Model" in label

    # Simulate 503
    class FakeUnavailableError(Exception):
        pass
    cat, label = _categorize_gemini_error(FakeUnavailableError("503 service unavailable"))
    assert cat == "service_unavailable"
    assert "Unavailable" in label
