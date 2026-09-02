"""
Admin User Management & Employee Provisioning API Router
Restricted to System Administrators (Role: ADMIN).
Provides employee invitation, role and clearance modification, account activation/revocation,
and full auditing of all organizational identity modifications.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.auth import AuthUser, get_current_user
from app.models.schemas import UserRole, ClassificationLevel
from app.services.user_service import user_service

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


def require_admin(current_user: Optional[AuthUser] = Depends(get_current_user)) -> AuthUser:
    """Dependency enforcing that the caller possesses administrator privileges."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden: Administrative privileges required.")
    return current_user


class InviteUserRequest(BaseModel):
    email: str
    display_name: str
    department: str
    job_title: str
    role: UserRole
    clearance_level: ClassificationLevel
    initial_password: str
    employee_id: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: UserRole
    reason: Optional[str] = None


class UpdateClearanceRequest(BaseModel):
    clearance_level: ClassificationLevel
    reason: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str  # "ACTIVE" | "DISABLED"
    reason: Optional[str] = None


@router.get("")
def list_employees(admin: AuthUser = Depends(require_admin)):
    """Lists all enterprise employees from the database."""
    users = user_service.list_users()
    return {
        "count": len(users),
        "users": users
    }


@router.post("/invite")
def invite_employee(req: InviteUserRequest, admin: AuthUser = Depends(require_admin)):
    """
    Provisions a new enterprise employee profile.
    Saves salted credentials in database and records a change audit log entry.
    """
    if len(req.initial_password) < 6:
        raise HTTPException(status_code=400, detail="Initial password must be at least 6 characters.")

    new_user = user_service.invite_user(
        admin_user_id=admin.user_id,
        admin_role=admin.role.value,
        email=req.email,
        display_name=req.display_name,
        department=req.department,
        job_title=req.job_title,
        role=req.role,
        clearance_level=req.clearance_level,
        initial_password=req.initial_password,
        employee_id=req.employee_id
    )
    return {
        "status": "success",
        "message": f"Employee profile created successfully for {req.display_name}.",
        "user": new_user
    }


@router.patch("/{user_id}/role")
def change_user_role(user_id: str, req: UpdateRoleRequest, admin: AuthUser = Depends(require_admin)):
    """Updates a user's role. Audited in change ledger."""
    updated = user_service.update_user_role(
        admin_user_id=admin.user_id,
        admin_role=admin.role.value,
        user_id=user_id,
        new_role=req.role,
        reason=req.reason
    )
    return {
        "status": "success",
        "message": f"User role updated to {req.role.value}.",
        "user": updated
    }


@router.patch("/{user_id}/clearance")
def change_user_clearance(user_id: str, req: UpdateClearanceRequest, admin: AuthUser = Depends(require_admin)):
    """Updates a user's clearance level. Audited in change ledger."""
    updated = user_service.update_user_clearance(
        admin_user_id=admin.user_id,
        admin_role=admin.role.value,
        user_id=user_id,
        new_clearance=req.clearance_level,
        reason=req.reason
    )
    return {
        "status": "success",
        "message": f"User clearance updated to {req.clearance_level.value}.",
        "user": updated
    }


@router.patch("/{user_id}/status")
def change_user_status(user_id: str, req: UpdateStatusRequest, admin: AuthUser = Depends(require_admin)):
    """Enables or disables an employee account. Audited in change ledger."""
    updated = user_service.update_user_status(
        admin_user_id=admin.user_id,
        admin_role=admin.role.value,
        user_id=user_id,
        new_status=req.status,
        reason=req.reason
    )
    return {
        "status": "success",
        "message": f"User account status changed to {req.status}.",
        "user": updated
    }
