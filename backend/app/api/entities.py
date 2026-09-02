from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.models.schemas import UserRole, EntityType, Entity
from app.core.auth import get_current_user, resolve_effective_role, AuthUser
from app.services.graph_service import graph_service
from app.services.permission_service import permission_service

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("")
def list_entities(
    role: Optional[UserRole] = Query(None),
    type: Optional[EntityType] = None,
    search: Optional[str] = None,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Lists all entities accessible to the role, with optional filtering by type and search term.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    entities = graph_service.get_all_entities(effective_role)
    
    if type:
        entities = [e for e in entities if e.type == type]

    if search:
        s_lower = search.lower()
        entities = [
            e for e in entities
            if s_lower in e.id.lower() or s_lower in e.name.lower() or s_lower in e.description.lower()
        ]

    return {
        "count": len(entities),
        "entities": entities
    }


@router.get("/{entity_id}")
def get_entity(
    entity_id: str,
    role: Optional[UserRole] = Query(None),
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Retrieves detailed metadata for a single entity if authorized.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    entity = graph_service.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    if not permission_service.is_authorized(effective_role, entity.classification):
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Role '{effective_role.value}' lacks clearance for {entity.classification.value} entity."
        )

    # Get immediate connected relationships
    all_rels = graph_service.get_all_relationships(effective_role)
    connected_rels = [
        r for r in all_rels
        if r.source_id == entity_id or r.target_id == entity_id
    ]

    return {
        "entity": entity,
        "connected_relationships": connected_rels
    }
