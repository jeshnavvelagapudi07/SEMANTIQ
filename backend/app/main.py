"""
SEMANTIQ FastAPI Application Entry Point
Permission-Aware Organizational Knowledge Graph & GraphRAG Reasoning System
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
from app.services.graph_service import graph_service
from app.api import (
    auth,
    admin_users,
    knowledge,
    queries,
    graph,
    entities,
    evidence,
    security,
    audit,
    actions,
    evaluation,
    health
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("semantiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown hooks."""
    logger.info("Initializing SEMANTIQ Database & Identity Layer...")
    init_db()
    logger.info("Initializing SEMANTIQ Knowledge Graph Engine...")
    graph_service.load_data(SEED_ENTITIES, SEED_RELATIONSHIPS)
    logger.info(f"Loaded {len(SEED_ENTITIES)} entities and {len(SEED_RELATIONSHIPS)} relationships.")
    ai_status = f"Gemini Live Connected ({settings.GEMINI_MODEL})" if settings.is_gemini_available else "Deterministic Development Fallback Active"
    logger.info(f"AI Provider Status: {ai_status}")
    logger.info(f"Deployment Environment: {settings.APP_ENV} | Port: {settings.PORT}")
    yield
    logger.info("SEMANTIQ Engine shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.TAGLINE,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(admin_users.router, prefix=settings.API_PREFIX)
app.include_router(knowledge.router, prefix=settings.API_PREFIX)
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(queries.router, prefix=settings.API_PREFIX)
app.include_router(graph.router, prefix=settings.API_PREFIX)
app.include_router(entities.router, prefix=settings.API_PREFIX)
app.include_router(evidence.router, prefix=settings.API_PREFIX)
app.include_router(security.router, prefix=settings.API_PREFIX)
app.include_router(audit.router, prefix=settings.API_PREFIX)
app.include_router(actions.router, prefix=settings.API_PREFIX)
app.include_router(evaluation.router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "ai_provider": f"Gemini Live ({settings.GEMINI_MODEL})" if settings.is_gemini_available else "Deterministic Fallback",
        "docs_url": "/docs",
        "health_url": f"{settings.API_PREFIX}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=not settings.is_production)
