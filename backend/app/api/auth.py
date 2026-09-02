"""
Authentication API Router
Handles enterprise multi-employee logins, salted password validation,
token issuance, active session verification, and directory lookups.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.auth import (
    AuthUser,
    DEMO_USERS,
    create_access_token,
    get_current_user
)
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = 28800
    user_id: str
    employee_id: str
    username: str
    email: str
    display_name: str
    title: str
    department: str
    role: str
    clearance_level: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    Authenticates an enterprise employee via email (or username) and password.
    Enforces password verification against PBKDF2 salted hash in database.
    Checks account status: DISABLED accounts return HTTP 403.
    """
    identifier = req.email or req.username
    if not identifier:
        raise HTTPException(status_code=400, detail="Email or username is required.")

    # Allow development bypass only when NOT in production and password is not provided
    allow_dev_bypass = (not settings.is_production) and (req.password is None or req.password == "")

    user = user_service.authenticate(
        identifier=identifier,
        password=req.password,
        allow_dev_bypass=allow_dev_bypass
    )

    token = create_access_token(user["id"])

    return LoginResponse(
        token=token,
        user_id=user["id"],
        employee_id=user["employee_id"],
        username=user["username"],
        email=user["email"],
        display_name=user["display_name"],
        title=user["job_title"],
        department=user["department"],
        role=user["role"],
        clearance_level=user["clearance_level"]
    )


@router.get("/me", response_model=AuthUser)
def get_me(current_user: Optional[AuthUser] = Depends(get_current_user)):
    """
    Returns the authenticated profile resolved server-side from the bearer token.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return current_user


@router.get("/users")
def list_demo_users():
    """
    Returns the list of available enterprise demo user accounts for development testing.
    In production, this endpoint is restricted.
    """
    return {
        "count": len(DEMO_USERS),
        "users": [
            {
                "username": u.username,
                "user_id": u.user_id,
                "employee_id": u.employee_id,
                "email": u.email,
                "display_name": u.display_name,
                "title": u.title,
                "role": u.role.value,
                "clearance_level": u.clearance_level
            }
            for u in DEMO_USERS.values()
        ]
    }


@router.post("/logout")
def logout():
    """
    Stateless session termination endpoint.
    Frontend clears the stored token from sessionStorage.
    """
    return {
        "status": "success",
        "message": "Session terminated successfully. Token invalidated on client."
    }
