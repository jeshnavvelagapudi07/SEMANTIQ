"""
User Management & Enterprise Identity Service
Handles database-backed user profiles, cryptographic authentication, role/clearance management,
account status (active/disabled), and change audit logging for administrative mutations.
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from app.core.database import get_db_connection, hash_password, verify_password
from app.models.schemas import UserRole, ClassificationLevel


class UserService:
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[dict]:
        """Retrieves a user profile by internal ID (excluding password hash/salt)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, auth_user_id, employee_id, username, email, display_name,
                       department, job_title, role, clearance_level, status, created_at, updated_at
                FROM users WHERE id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def get_user_by_email_or_username(identifier: str) -> Optional[dict]:
        """Retrieves a user profile including credentials by email or username."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, auth_user_id, employee_id, username, email, password_hash, salt,
                       display_name, department, job_title, role, clearance_level, status,
                       created_at, updated_at
                FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
            """, (identifier.strip(), identifier.strip()))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def authenticate(identifier: str, password: Optional[str] = None, allow_dev_bypass: bool = False) -> dict:
        """
        Authenticates a user via email or username with password validation.
        Enforces status check: DISABLED accounts return HTTP 403.
        Invalid credentials return HTTP 401.
        """
        user = UserService.get_user_by_email_or_username(identifier)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials. Account was not found in directory."
            )

        if user["status"] == "DISABLED":
            raise HTTPException(
                status_code=403,
                detail="Account is disabled. Access revoked by system administrator."
            )

        # In non-dev/test environments, password is strictly mandatory
        if password:
            if not verify_password(password, user["password_hash"], user["salt"]):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials. Incorrect password."
                )
        elif not allow_dev_bypass:
            raise HTTPException(
                status_code=401,
                detail="Password is required to authenticate."
            )

        # Return public profile (never expose password_hash or salt)
        clean_user = {k: v for k, v in user.items() if k not in ("password_hash", "salt")}
        return clean_user

    @staticmethod
    def list_users() -> list[dict]:
        """Returns all registered employees in the enterprise directory (admin view)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, employee_id, username, email, display_name, department,
                       job_title, role, clearance_level, status, created_at, updated_at
                FROM users ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def invite_user(
        admin_user_id: str,
        admin_role: str,
        email: str,
        display_name: str,
        department: str,
        job_title: str,
        role: UserRole,
        clearance_level: ClassificationLevel,
        initial_password: str,
        employee_id: Optional[str] = None
    ) -> dict:
        """Creates a new employee profile in the database and records an audit log entry."""
        if admin_role != UserRole.ADMIN.value and admin_role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can provision new users.")

        email_clean = email.strip().lower()
        if UserService.get_user_by_email_or_username(email_clean):
            raise HTTPException(status_code=400, detail=f"User with email '{email_clean}' already exists.")

        now = datetime.now(timezone.utc).isoformat()
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        auth_user_id = f"auth_{uuid.uuid4().hex[:8]}"

        # Auto-generate employee ID if omitted
        if not employee_id:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM users")
                cnt = cursor.fetchone()["cnt"] + 1
                employee_id = f"EMP-{cnt:03d}"

        # Generate username from email prefix
        base_username = email_clean.split("@")[0].replace(".", "_")
        username = base_username

        p_hash, salt = hash_password(initial_password)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    id, auth_user_id, employee_id, username, email,
                    password_hash, salt, display_name, department,
                    job_title, role, clearance_level, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, auth_user_id, employee_id, username, email_clean,
                p_hash, salt, display_name, department,
                job_title, role.value, clearance_level.value, "ACTIVE",
                now, now
            ))

            # Audit log entry
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, admin_user_id, admin_role, "USER_INVITE",
                user_id, "USER", None,
                json.dumps({
                    "email": email_clean,
                    "employee_id": employee_id,
                    "role": role.value,
                    "clearance_level": clearance_level.value,
                    "department": department
                }),
                f"Administrator provisioned new employee account for {display_name}."
            ))
            conn.commit()

        return UserService.get_user_by_id(user_id)

    @staticmethod
    def update_user_role(admin_user_id: str, admin_role: str, user_id: str, new_role: UserRole, reason: Optional[str] = None) -> dict:
        """Updates a user's role. Strictly audited."""
        if admin_role != UserRole.ADMIN.value and admin_role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can modify user roles.")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        old_role = user["role"]
        if old_role == new_role.value:
            return user

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ?, updated_at = ? WHERE id = ?", (new_role.value, now, user_id))

            # Audit log
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, admin_user_id, admin_role, "USER_ROLE_CHANGE",
                user_id, "USER", json.dumps({"role": old_role}),
                json.dumps({"role": new_role.value}),
                reason or f"Role updated from {old_role} to {new_role.value}"
            ))
            conn.commit()

        return UserService.get_user_by_id(user_id)

    @staticmethod
    def update_user_clearance(admin_user_id: str, admin_role: str, user_id: str, new_clearance: ClassificationLevel, reason: Optional[str] = None) -> dict:
        """Updates a user's clearance level. Strictly audited."""
        if admin_role != UserRole.ADMIN.value and admin_role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can modify clearance levels.")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        old_clearance = user["clearance_level"]
        if old_clearance == new_clearance.value:
            return user

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET clearance_level = ?, updated_at = ? WHERE id = ?", (new_clearance.value, now, user_id))

            # Audit log
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, admin_user_id, admin_role, "USER_CLEARANCE_CHANGE",
                user_id, "USER", json.dumps({"clearance_level": old_clearance}),
                json.dumps({"clearance_level": new_clearance.value}),
                reason or f"Clearance updated from {old_clearance} to {new_clearance.value}"
            ))
            conn.commit()

        return UserService.get_user_by_id(user_id)

    @staticmethod
    def update_user_status(admin_user_id: str, admin_role: str, user_id: str, new_status: str, reason: Optional[str] = None) -> dict:
        """Enables or disables an employee account. Strictly audited."""
        if admin_role != UserRole.ADMIN.value and admin_role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can change user account status.")

        if new_status not in ("ACTIVE", "DISABLED", "INVITED"):
            raise HTTPException(status_code=400, detail="Invalid status. Must be ACTIVE, DISABLED, or INVITED.")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Prevent admin from disabling their own account
        if user_id == admin_user_id and new_status == "DISABLED":
            raise HTTPException(status_code=400, detail="Administrators cannot disable their own account.")

        old_status = user["status"]
        if old_status == new_status:
            return user

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, user_id))

            # Audit log
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, admin_user_id, admin_role, "USER_STATUS_CHANGE",
                user_id, "USER", json.dumps({"status": old_status}),
                json.dumps({"status": new_status}),
                reason or f"Account status transitioned to {new_status}"
            ))
            conn.commit()

        return UserService.get_user_by_id(user_id)


user_service = UserService()
