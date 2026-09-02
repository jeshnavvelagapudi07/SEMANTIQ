from typing import Optional
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from app.models.schemas import UserRole, ClassificationLevel
from app.core.auth import get_current_user, resolve_effective_role, AuthUser
from app.services.permission_service import permission_service, ROLE_CLEARANCE
from app.services.graph_service import graph_service
from app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/security", tags=["Security & Permissions"])


class PermissionSimulateRequest(BaseModel):
    role: Optional[UserRole] = None
    target_entity_ids: list[str]


@router.get("/me")
def get_security_profile(
    role: Optional[UserRole] = Query(None),
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Returns security clearance, accessible vs restricted counts for the current role.
    Uses server-side resolved role when authenticated.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    all_entities = list(graph_service.entities_by_id.values())
    all_docs = retrieval_service.documents
    all_evidence = retrieval_service.evidence_chunks

    auth_entities, filtered_entities = permission_service.filter_entities(effective_role, all_entities)
    auth_docs, filtered_docs = permission_service.filter_documents(effective_role, all_docs)
    auth_ev, filtered_ev = permission_service.filter_evidence(effective_role, all_evidence)

    allowed_levels = [lvl.value for lvl in ROLE_CLEARANCE.get(effective_role, set())]

    return {
        "current_role": effective_role.value,
        "authorized_classification_levels": allowed_levels,
        "accessible_summary": {
            "entities": {
                "accessible": len(auth_entities),
                "restricted": len(filtered_entities),
                "total": len(all_entities)
            },
            "documents": {
                "accessible": len(auth_docs),
                "restricted": len(filtered_docs),
                "total": len(all_docs)
            },
            "evidence_chunks": {
                "accessible": len(auth_ev),
                "restricted": len(filtered_ev),
                "total": len(all_evidence)
            }
        },
        "restricted_entities_preview": [f.model_dump() for f in filtered_entities[:5]],
        "restricted_docs_preview": [f.model_dump() for f in filtered_docs[:5]]
    }


@router.get("/matrix")
def get_matrix():
    """
    Returns the complete role-to-classification clearance matrix.
    """
    return {
        "roles": [r.value for r in UserRole],
        "classifications": [c.value for c in ClassificationLevel],
        "matrix": permission_service.get_security_matrix()
    }


@router.post("/simulate")
def simulate_permission_check(req: PermissionSimulateRequest):
    """
    Interactive security test endpoint: Simulates attempting to access target entities
    under a given role, demonstrating the pre-LLM filter boundary.
    """
    targets = [
        graph_service.get_entity(eid) for eid in req.target_entity_ids
        if graph_service.get_entity(eid) is not None
    ]
    
    authorized, filtered = permission_service.filter_entities(req.role, targets)

    return {
        "role": req.role.value,
        "input_entities_count": len(targets),
        "authorized_count": len(authorized),
        "filtered_count": len(filtered),
        "authorized_entities": [e.id for e in authorized],
        "filtered_details": [f.model_dump() for f in filtered],
        "zero_leakage_guarantee": "Filtered entities are strictly pruned BEFORE graph traversal or LLM prompt generation."
    }
