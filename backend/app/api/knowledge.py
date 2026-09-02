"""
Knowledge Management API Router
Handles role-based entity & relationship creation, optimistic version locking,
provenance tracking, human verification workflow (approve/reject), and change audit queries.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any

from app.core.auth import AuthUser, get_current_user, resolve_effective_role
from app.models.schemas import UserRole, ClassificationLevel
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["Knowledge Management"])


class CreateEntityRequest(BaseModel):
    id: str
    type: str  # "PROJECT", "SYSTEM", "TEAM", "INCIDENT", "DOCUMENT", "SOP", "POLICY"
    name: str
    description: str
    access_tier: ClassificationLevel = ClassificationLevel.INTERNAL
    owner_team: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    role: Optional[UserRole] = None


class UpdateEntityRequest(BaseModel):
    version: int
    name: Optional[str] = None
    description: Optional[str] = None
    access_tier: Optional[ClassificationLevel] = None
    owner_team: Optional[str] = None
    properties: Optional[dict[str, Any]] = None
    role: Optional[UserRole] = None


class ArchiveEntityRequest(BaseModel):
    reason: Optional[str] = None
    role: Optional[UserRole] = None


class CreateRelationshipRequest(BaseModel):
    source_entity_id: str
    relationship_type: str
    target_entity_id: str
    evidence_ids: Optional[list[str]] = None
    description: Optional[str] = None
    access_tier: Optional[ClassificationLevel] = None
    role: Optional[UserRole] = None


class VerifyDecisionRequest(BaseModel):
    comment: Optional[str] = None
    role: Optional[UserRole] = None


@router.get("/entities")
def list_entities(
    status: Optional[str] = "ACTIVE",
    type: Optional[str] = None,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Lists entities accessible under user clearance, filtering by status and type."""
    role, _ = resolve_effective_role(current_user)
    entities = knowledge_service.list_entities(role, status=status, entity_type=type)
    return {"count": len(entities), "entities": entities}


@router.get("/entities/{entity_id}")
def get_entity(
    entity_id: str,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Retrieves a single entity by ID."""
    role, _ = resolve_effective_role(current_user)
    ent = knowledge_service.get_entity_by_id(entity_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return ent


@router.post("/entities")
def create_entity(
    req: CreateEntityRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Creates a new knowledge entity with strict role-based type & clearance checks.
    Server-side role overrides any client-supplied role.
    """
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    new_ent = knowledge_service.create_entity(
        creator_id=effective_user_id,
        creator_role=effective_role,
        entity_id=req.id.strip().upper(),
        entity_type=req.type,
        name=req.name.strip(),
        description=req.description.strip(),
        access_tier=req.access_tier,
        owner_team=req.owner_team,
        properties=req.properties
    )
    return {"status": "success", "entity": new_ent}


@router.patch("/entities/{entity_id}")
def update_entity(
    entity_id: str,
    req: UpdateEntityRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Updates an entity with optimistic version locking to prevent concurrent overwrite."""
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    updated = knowledge_service.update_entity(
        updater_id=effective_user_id,
        updater_role=effective_role,
        entity_id=entity_id,
        expected_version=req.version,
        name=req.name,
        description=req.description,
        access_tier=req.access_tier,
        owner_team=req.owner_team,
        properties=req.properties
    )
    return {"status": "success", "entity": updated}


@router.post("/entities/{entity_id}/archive")
def archive_entity(
    entity_id: str,
    req: ArchiveEntityRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Soft-archives an entity, preserving audit history while pruning from active operational graph."""
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    archived = knowledge_service.archive_entity(
        actor_id=effective_user_id,
        actor_role=effective_role,
        entity_id=entity_id,
        reason=req.reason
    )
    return {"status": "success", "entity": archived}


@router.get("/relationships")
def list_relationships(
    status: Optional[str] = None,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Lists relationships accessible under user clearance, filtering by verification status."""
    role, _ = resolve_effective_role(current_user)
    relationships = knowledge_service.list_relationships(role, status=status)
    return {"count": len(relationships), "relationships": relationships}


@router.get("/relationships/pending")
def list_pending_relationships(
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Retrieves relationships awaiting human verification."""
    role, _ = resolve_effective_role(current_user)
    if role == UserRole.VIEWER:
        return {"count": 0, "relationships": []}
    pending = knowledge_service.list_relationships(role, status="PENDING_VERIFICATION")
    return {"count": len(pending), "relationships": pending}


@router.post("/relationships")
def create_relationship(
    req: CreateRelationshipRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Proposes a new knowledge graph relationship.
    Enforces integrity: source/target existence, prohibited self-loops, duplicate avoidance.
    Starts in PENDING_VERIFICATION unless created by Administrator.
    """
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    rel = knowledge_service.create_relationship(
        creator_id=effective_user_id,
        creator_role=effective_role,
        source_id=req.source_entity_id.strip().upper(),
        relationship_type=req.relationship_type.strip().upper(),
        target_id=req.target_entity_id.strip().upper(),
        evidence_ids=req.evidence_ids,
        description=req.description,
        access_tier=req.access_tier
    )
    return {"status": "success", "relationship": rel}


@router.post("/relationships/{rel_id}/verify")
def verify_relationship(
    rel_id: str,
    req: VerifyDecisionRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Human reviewer approves a relationship for active authoritative GraphRAG reasoning."""
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    verified = knowledge_service.verify_relationship(
        reviewer_id=effective_user_id,
        reviewer_role=effective_role,
        rel_id=rel_id,
        comment=req.comment
    )
    return {"status": "success", "relationship": verified}


@router.post("/relationships/{rel_id}/reject")
def reject_relationship(
    rel_id: str,
    req: VerifyDecisionRequest,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Human reviewer rejects a proposed relationship."""
    effective_role, effective_user_id = resolve_effective_role(current_user, client_supplied_role=req.role)
    rejected = knowledge_service.reject_relationship(
        reviewer_id=effective_user_id,
        reviewer_role=effective_role,
        rel_id=rel_id,
        comment=req.comment
    )
    return {"status": "success", "relationship": rejected}


@router.get("/changes")
def get_change_audit_logs(
    limit: int = 50,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """Retrieves change audit ledger entries."""
    role, _ = resolve_effective_role(current_user)
    logs = knowledge_service.get_change_audit_logs(limit=limit)
    return {"count": len(logs), "changes": logs}
