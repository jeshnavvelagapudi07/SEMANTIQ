from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.models.schemas import UserRole, EvidenceChunk, Document
from app.core.auth import get_current_user, resolve_effective_role, AuthUser
from app.services.retrieval_service import retrieval_service
from app.services.permission_service import permission_service

router = APIRouter(prefix="/evidence", tags=["Evidence & Documents"])


@router.get("")
def list_evidence(
    role: Optional[UserRole] = Query(None),
    search: Optional[str] = None,
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Lists all authorized evidence chunks with optional search filter.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    authorized_chunks, _ = permission_service.filter_evidence(effective_role, retrieval_service.evidence_chunks)
    
    if search:
        s_lower = search.lower()
        authorized_chunks = [
            ev for ev in authorized_chunks
            if s_lower in ev.id.lower() or s_lower in ev.doc_title.lower() or s_lower in ev.excerpt.lower()
        ]

    return {
        "count": len(authorized_chunks),
        "evidence": authorized_chunks
    }


@router.get("/{evidence_id}")
def get_evidence_detail(
    evidence_id: str,
    role: Optional[UserRole] = Query(None),
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Retrieves full evidence chunk details and parent document metadata.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    chunk = retrieval_service.get_evidence_chunk(evidence_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found.")

    if not permission_service.is_authorized(effective_role, chunk.classification):
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Evidence '{evidence_id}' is classified as {chunk.classification.value}."
        )

    parent_doc = retrieval_service.get_document(chunk.doc_id)

    return {
        "evidence": chunk,
        "parent_document": parent_doc
    }


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: str,
    role: UserRole = Query(UserRole.OPERATIONS_ENGINEER)
):
    """
    Retrieves a complete document if authorized.
    """
    doc = retrieval_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    if not permission_service.is_authorized(role, doc.classification):
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Document '{doc_id}' is classified as {doc.classification.value}."
        )

    return doc
