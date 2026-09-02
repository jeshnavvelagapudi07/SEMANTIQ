"""
Health & System Status API Router
Provides system health check and safe AI runtime status without exposing secrets.
The /api/system/ai-status endpoint performs a real minimal Gemini probe to verify
actual connectivity, not just whether the environment variable exists.
CRITICAL: This endpoint NEVER returns the API key or any partial key.
"""
import asyncio
import logging
from fastapi import APIRouter
from app.core.config import settings
from app.services.graph_service import graph_service
from app.models.schemas import UserRole

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health & Status"])


# ──────────────────────────────────────────────────────────────────────────────
# Internal Gemini probe — async, minimal, key-safe
# ──────────────────────────────────────────────────────────────────────────────

async def _probe_gemini() -> tuple[bool, str]:
    """
    Performs one minimal Gemini request to confirm actual API connectivity.
    Returns (success: bool, status_string: str).
    NEVER includes the API key in any returned string or log message.
    """
    if not settings.is_gemini_available:
        return False, "unconfigured"

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Respond with exactly one word: OK",
            config=types.GenerateContentConfig(temperature=0.0)
        )
        text = (response.text or "").strip()
        if text:
            logger.info(f"Gemini probe: success | model: {settings.GEMINI_MODEL}")
            return True, "live"
        else:
            logger.warning(f"Gemini probe: empty response | model: {settings.GEMINI_MODEL}")
            return False, "invalid_response"

    except Exception as exc:
        err_str = str(exc).lower()
        exc_type = type(exc).__name__

        # Categorize without exposing key
        if "401" in err_str or "403" in err_str or "unauthenticated" in err_str or "permission_denied" in err_str:
            status = "authentication_error"
        elif "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
            status = "quota_error"
        elif "404" in err_str or "not_found" in err_str or "no longer available" in err_str:
            status = "model_error"
        elif "503" in err_str or "502" in err_str or "unavailable" in err_str:
            status = "service_unavailable"
        elif "timeout" in err_str or "deadline" in err_str or "timed out" in err_str:
            status = "timeout"
        elif "network" in err_str or "connection" in err_str or "ssl" in err_str:
            status = "network_error"
        else:
            status = "api_error"

        logger.warning(
            f"Gemini probe: {status} | model: {settings.GEMINI_MODEL} | "
            f"error_type: {exc_type}"
        )
        return False, status


@router.get("/health")
def health_check():
    """
    Returns system status, active provider, node/edge counts, and environment.
    """
    stats = graph_service.get_stats(UserRole.ADMIN)
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "tagline": settings.TAGLINE,
        "environment": settings.APP_ENV,
        "ai_provider": f"Gemini ({settings.GEMINI_MODEL})" if settings.is_gemini_available else "Deterministic Fallback (No Gemini Key)",
        "is_gemini_configured": settings.is_gemini_available,
        "knowledge_graph": {
            "nodes": stats["total_nodes"],
            "edges": stats["total_edges"],
            "entity_types": stats["entity_types"]
        }
    }


@router.get("/system/ai-status")
async def get_ai_status():
    """
    Returns safe AI provider status and model configuration.
    Performs a real minimal Gemini probe to confirm actual connectivity.

    CRITICAL SECURITY RULES enforced in this endpoint:
    - NEVER returns the API key.
    - NEVER returns a partial API key.
    - NEVER logs the API key.
    - The 'status' field reflects actual API connectivity, not just key presence.
    """
    if not settings.is_gemini_available:
        return {
            "provider": "gemini",
            "configured": False,
            "available": False,
            "model": settings.GEMINI_MODEL,
            "status": "unconfigured"
        }

    # Run real probe with a 10-second timeout
    try:
        available, status = await asyncio.wait_for(_probe_gemini(), timeout=10.0)
    except asyncio.TimeoutError:
        available, status = False, "timeout"
    except Exception:
        available, status = False, "api_error"

    return {
        "provider": "gemini",
        "configured": True,
        "available": available,
        "model": settings.GEMINI_MODEL,
        "status": status
    }
