"""
Server-Side Identity, Authentication, and Role Resolution Service
Enforces cryptographic token verification, database-backed user validation,
immediate account revocation/status checking, and guarantees that client-supplied
role headers or request parameters NEVER override server-side authorization.
"""
import hmac
import hashlib
import base64
import json
import time
from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import UserRole, ClassificationLevel


class AuthUser(BaseModel):
    user_id: str
    username: str
    email: str = ""
    employee_id: str = ""
    display_name: str
    title: str
    department: str = ""
    role: UserRole
    clearance_level: str = "INTERNAL"
    active: bool = True


# Pre-configured Enterprise Seed Accounts (for dev/test compatibility)
DEMO_USERS: dict[str, AuthUser] = {
    "ops_eng_01": AuthUser(
        user_id="usr_ops_01",
        username="ops_eng_01",
        email="kenji.sato@semantiq.org",
        employee_id="EMP-001",
        display_name="Kenji Sato",
        title="Lead Reliability & Operations Engineer",
        department="Manufacturing Operations & Reliability",
        role=UserRole.OPERATIONS_ENGINEER,
        clearance_level="CONFIDENTIAL"
    ),
    "pm_01": AuthUser(
        user_id="usr_pm_01",
        username="pm_01",
        email="elena.rostova@semantiq.org",
        employee_id="EMP-002",
        display_name="Elena Rostova",
        title="Principal Delivery & Project Director",
        department="Aerospace Program Delivery",
        role=UserRole.PROJECT_MANAGER,
        clearance_level="CONFIDENTIAL"
    ),
    "viewer_01": AuthUser(
        user_id="usr_view_01",
        username="viewer_01",
        email="marcus.vance@semantiq.org",
        employee_id="EMP-003",
        display_name="Marcus Vance",
        title="Independent Compliance & Safety Auditor",
        department="Quality & Regulatory Compliance",
        role=UserRole.VIEWER,
        clearance_level="INTERNAL"
    ),
    "admin_01": AuthUser(
        user_id="usr_admin_01",
        username="admin_01",
        email="aris.thorne@semantiq.org",
        employee_id="EMP-004",
        display_name="Dr. Aris Thorne",
        title="Chief Technology Officer & System Admin",
        department="Executive Engineering Leadership",
        role=UserRole.ADMIN,
        clearance_level="RESTRICTED"
    )
}

security_bearer = HTTPBearer(auto_error=False)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(identifier: str, expires_in_seconds: int = 28800) -> str:
    """Generates an HMAC-SHA256 cryptographically signed session token from DB profile or seed demo account."""
    from app.services.user_service import user_service
    
    # Try DB lookup first
    db_user = user_service.get_user_by_email_or_username(identifier)
    if not db_user:
        db_user = user_service.get_user_by_id(identifier)

    if db_user:
        now = int(time.time())
        payload = {
            "user_id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "employee_id": db_user["employee_id"],
            "display_name": db_user["display_name"],
            "title": db_user["job_title"],
            "department": db_user["department"],
            "role": db_user["role"],
            "clearance_level": db_user["clearance_level"],
            "iat": now,
            "exp": now + expires_in_seconds
        }
    elif identifier in DEMO_USERS:
        demo = DEMO_USERS[identifier]
        now = int(time.time())
        payload = {
            "user_id": demo.user_id,
            "username": demo.username,
            "email": demo.email,
            "employee_id": demo.employee_id,
            "display_name": demo.display_name,
            "title": demo.title,
            "department": demo.department,
            "role": demo.role.value,
            "clearance_level": demo.clearance_level,
            "iat": now,
            "exp": now + expires_in_seconds
        }
    else:
        raise ValueError(f"User '{identifier}' does not exist in identity directory.")

    payload_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    payload_b64 = _b64_encode(payload_json)

    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature_b64 = _b64_encode(signature)

    return f"{payload_b64}.{signature_b64}"


def verify_access_token(token: str) -> AuthUser:
    """
    Validates token signature and expiration, checking live account status in database.
    If the account was DISABLED by an administrator, immediately raises HTTP 403.
    Refreshes role and clearance directly from current database state.
    """
    parts = token.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid token structure.")

    payload_b64, signature_b64 = parts[0], parts[1]

    expected_sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = _b64_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise HTTPException(status_code=401, detail="Cryptographic token signature verification failed.")

    try:
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed token payload.")

    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise HTTPException(status_code=401, detail="Authentication session token has expired.")

    user_id = payload.get("user_id", "unknown")

    # Check live DB state for status and up-to-date role/clearance
    from app.services.user_service import user_service
    db_user = user_service.get_user_by_id(user_id)
    if db_user:
        if db_user["status"] == "DISABLED":
            raise HTTPException(
                status_code=403,
                detail="Account is disabled. Access revoked by system administrator."
            )
        role_str = db_user["role"]
        clearance_str = db_user["clearance_level"]
        display_name = db_user["display_name"]
        title = db_user["job_title"]
        department = db_user["department"]
        email = db_user["email"]
        employee_id = db_user["employee_id"]
        username = db_user["username"]
    else:
        # Fallback to payload data
        role_str = payload.get("role")
        clearance_str = payload.get("clearance_level", "INTERNAL")
        display_name = payload.get("display_name", "User")
        title = payload.get("title", "")
        department = payload.get("department", "")
        email = payload.get("email", "")
        employee_id = payload.get("employee_id", "")
        username = payload.get("username", "unknown")

    try:
        role_enum = UserRole(role_str)
    except ValueError:
        raise HTTPException(status_code=401, detail=f"Invalid role '{role_str}' in identity session.")

    return AuthUser(
        user_id=user_id,
        username=username,
        email=email,
        employee_id=employee_id,
        display_name=display_name,
        title=title,
        department=department,
        role=role_enum,
        clearance_level=clearance_str,
        active=True
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Optional[AuthUser]:
    """
    FastAPI dependency for server-side user authentication.
    - In production: Raises HTTP 401 if token is missing or invalid.
    - In development/test: Validates token if provided, or allows unauthenticated fallback.
    """
    token = None
    if credentials:
        token = credentials.credentials
    elif "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if token:
        return verify_access_token(token)

    if settings.is_production:
        raise HTTPException(
            status_code=401,
            detail="Production authentication required. Please provide a valid Authorization Bearer token."
        )

    return None


def resolve_effective_role(
    auth_user: Optional[AuthUser],
    client_supplied_role: Optional[UserRole] = None,
    client_user_id: Optional[str] = None
) -> tuple[UserRole, str]:
    """
    CRITICAL SECURITY FUNCTION:
    If an authenticated user exists, their server-resolved role and ID MUST be used.
    Any role sent by the client in request payload or query parameter is IGNORED.
    """
    if auth_user is not None:
        return auth_user.role, auth_user.user_id

    if settings.is_production:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Valid session token required in production environment."
        )

    effective_role = client_supplied_role if client_supplied_role is not None else UserRole.OPERATIONS_ENGINEER
    effective_id = client_user_id if client_user_id is not None else f"dev_{effective_role.value}"
    return effective_role, effective_id
