"""
Human-in-the-Loop Actions API Router
Endpoints for human review, approval, and rejection of AI suggested operational actions.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ActionItem, ActionDecisionRequest
from app.services.action_service import action_service

router = APIRouter(prefix="/actions", tags=["Human-in-the-Loop Actions"])


@router.get("")
def list_actions():
    """
    Returns all operational action items.
    """
    actions = action_service.get_all_actions()
    return {
        "count": len(actions),
        "actions": actions
    }


@router.get("/{action_id}")
def get_action(action_id: str):
    action = action_service.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found.")
    return action


@router.post("/{action_id}/approve", response_model=ActionItem)
def approve_action(action_id: str, req: ActionDecisionRequest):
    """
    Approves an action item and updates audit logs.
    """
    updated = action_service.approve_action(action_id, reviewed_by=req.user_id, comment=req.comment)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found.")
    return updated


@router.post("/{action_id}/reject", response_model=ActionItem)
def reject_action(action_id: str, req: ActionDecisionRequest):
    """
    Rejects an action item and updates audit logs.
    """
    updated = action_service.reject_action(action_id, reviewed_by=req.user_id, comment=req.comment)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found.")
    return updated
