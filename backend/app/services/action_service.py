"""
Action Service
Manages Human-in-the-Loop operational action recommendations, review workflows, and status tracking.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.models.schemas import (
    ActionItem,
    ActionStatus
)
from app.core.database import get_db_connection
from app.services.audit_service import audit_service


class ActionService:
    def __init__(self):
        pass  # Tables are created by database.init_db() at application startup.

    def _get_connection(self):
        return get_db_connection()

    def create_action(
        self,
        query_id: str,
        title: str,
        description: str,
        target_entity: str
    ) -> ActionItem:
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO action_items (
                    id, query_id, title, description, target_entity,
                    status, created_at, reviewed_by, reviewed_at, resolution_comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action_id, query_id, title, description, target_entity,
                ActionStatus.PENDING.value, created_at, None, None, None
            ))
            conn.commit()

        return ActionItem(
            id=action_id,
            query_id=query_id,
            title=title,
            description=description,
            target_entity=target_entity,
            status=ActionStatus.PENDING,
            created_at=created_at
        )

    def approve_action(
        self,
        action_id: str,
        reviewed_by: str = "usr_approver_01",
        comment: Optional[str] = None
    ) -> Optional[ActionItem]:
        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE action_items
                SET status = ?, reviewed_by = ?, reviewed_at = ?, resolution_comment = ?
                WHERE id = ?
            """, (ActionStatus.APPROVED.value, reviewed_by, reviewed_at, comment or "Approved by operator.", action_id))
            conn.commit()

        audit_service.update_action_status(action_id, ActionStatus.APPROVED)
        return self.get_action(action_id)

    def reject_action(
        self,
        action_id: str,
        reviewed_by: str = "usr_approver_01",
        comment: Optional[str] = None
    ) -> Optional[ActionItem]:
        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE action_items
                SET status = ?, reviewed_by = ?, reviewed_at = ?, resolution_comment = ?
                WHERE id = ?
            """, (ActionStatus.REJECTED.value, reviewed_by, reviewed_at, comment or "Rejected by operator.", action_id))
            conn.commit()

        audit_service.update_action_status(action_id, ActionStatus.REJECTED)
        return self.get_action(action_id)

    def get_action(self, action_id: str) -> Optional[ActionItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_items WHERE id = ?", (action_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ActionItem(
                id=row["id"],
                query_id=row["query_id"],
                title=row["title"],
                description=row["description"],
                target_entity=row["target_entity"],
                status=ActionStatus(row["status"]),
                created_at=row["created_at"],
                reviewed_by=row["reviewed_by"],
                reviewed_at=row["reviewed_at"],
                resolution_comment=row["resolution_comment"]
            )

    def get_all_actions(self) -> list[ActionItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_items ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [
                ActionItem(
                    id=r["id"],
                    query_id=r["query_id"],
                    title=r["title"],
                    description=r["description"],
                    target_entity=r["target_entity"],
                    status=ActionStatus(r["status"]),
                    created_at=r["created_at"],
                    reviewed_by=r["reviewed_by"],
                    reviewed_at=r["reviewed_at"],
                    resolution_comment=r["resolution_comment"]
                )
                for r in rows
            ]


action_service = ActionService()
