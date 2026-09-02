"""
Audit Log API Router
Exposes query execution history and detailed audit logs.
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("")
def list_audit_logs(limit: int = Query(50, ge=1, le=200)):
    """
    Returns recent query execution audit logs.
    """
    logs = audit_service.get_logs(limit=limit)
    return {
        "count": len(logs),
        "logs": logs
    }


@router.get("/{query_id}")
def get_audit_log(query_id: str):
    """
    Retrieves full audit trace for a specific query execution.
    """
    log = audit_service.get_log(query_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Audit record '{query_id}' not found.")
    return log
