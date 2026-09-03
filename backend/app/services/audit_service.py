"""
Audit Service
PostgreSQL-backed Audit Trail recording queries, permission filtering, LLM inputs, citations, and human approvals.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.models.schemas import (
    AuditLogEntry,
    UserRole,
    ActionStatus
)
from app.core.database import get_db_connection


class AuditService:
    def __init__(self):
        pass  # Tables are created by database.init_db() at application startup.

    def _get_connection(self):
        return get_db_connection()

    def log_query(
        self,
        query_id: str,
        user_id: str,
        user_role: UserRole,
        query: str,
        identified_entities: list[str],
        authorized_entities: list[str],
        filtered_entities_count: int,
        filtered_details: list[dict],
        graph_paths_count: int,
        evidence_ids: list[str],
        llm_provider: str,
        validation_status: str,
        confidence_score: float,
        confidence_level: str,
        recommendation: Optional[str],
        requires_human_review: bool,
        action_id: Optional[str] = None,
        action_status: Optional[ActionStatus] = None
    ) -> AuditLogEntry:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (
                    id, timestamp, user_id, user_role, query,
                    identified_entities, authorized_entities, filtered_entities_count, filtered_details,
                    graph_paths_count, evidence_ids, llm_provider, validation_status,
                    confidence_score, confidence_level, recommendation, requires_human_review,
                    action_id, action_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    timestamp = EXCLUDED.timestamp,
                    user_id = EXCLUDED.user_id,
                    user_role = EXCLUDED.user_role,
                    query = EXCLUDED.query,
                    identified_entities = EXCLUDED.identified_entities,
                    authorized_entities = EXCLUDED.authorized_entities,
                    filtered_entities_count = EXCLUDED.filtered_entities_count,
                    filtered_details = EXCLUDED.filtered_details,
                    graph_paths_count = EXCLUDED.graph_paths_count,
                    evidence_ids = EXCLUDED.evidence_ids,
                    llm_provider = EXCLUDED.llm_provider,
                    validation_status = EXCLUDED.validation_status,
                    confidence_score = EXCLUDED.confidence_score,
                    confidence_level = EXCLUDED.confidence_level,
                    recommendation = EXCLUDED.recommendation,
                    requires_human_review = EXCLUDED.requires_human_review,
                    action_id = EXCLUDED.action_id,
                    action_status = EXCLUDED.action_status
            """, (
                query_id,
                timestamp,
                user_id,
                user_role.value,
                query,
                json.dumps(identified_entities),
                json.dumps(authorized_entities),
                filtered_entities_count,
                json.dumps(filtered_details),
                graph_paths_count,
                json.dumps(evidence_ids),
                llm_provider,
                validation_status,
                confidence_score,
                confidence_level,
                recommendation or "",
                1 if requires_human_review else 0,
                action_id or "",
                action_status.value if action_status else ""
            ))
            conn.commit()

        return AuditLogEntry(
            id=query_id,
            timestamp=timestamp,
            user_id=user_id,
            user_role=user_role,
            query=query,
            identified_entities=identified_entities,
            authorized_entities=authorized_entities,
            filtered_entities_count=filtered_entities_count,
            graph_paths_count=graph_paths_count,
            evidence_ids=evidence_ids,
            llm_provider=llm_provider,
            validation_status=validation_status,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            recommendation=recommendation,
            requires_human_review=requires_human_review,
            action_id=action_id,
            action_status=action_status
        )

    def get_logs(self, limit: int = 100) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "user_id": r["user_id"],
                    "user_role": r["user_role"],
                    "query": r["query"],
                    "identified_entities": json.loads(r["identified_entities"] or "[]"),
                    "authorized_entities": json.loads(r["authorized_entities"] or "[]"),
                    "filtered_entities_count": r["filtered_entities_count"],
                    "filtered_details": json.loads(r["filtered_details"] or "[]"),
                    "graph_paths_count": r["graph_paths_count"],
                    "evidence_ids": json.loads(r["evidence_ids"] or "[]"),
                    "llm_provider": r["llm_provider"],
                    "validation_status": r["validation_status"],
                    "confidence_score": r["confidence_score"],
                    "confidence_level": r["confidence_level"],
                    "recommendation": r["recommendation"],
                    "requires_human_review": bool(r["requires_human_review"]),
                    "action_id": r["action_id"],
                    "action_status": r["action_status"]
                })
            return results

    def get_log(self, log_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "user_id": row["user_id"],
                "user_role": row["user_role"],
                "query": row["query"],
                "identified_entities": json.loads(row["identified_entities"] or "[]"),
                "authorized_entities": json.loads(row["authorized_entities"] or "[]"),
                "filtered_entities_count": row["filtered_entities_count"],
                "filtered_details": json.loads(row["filtered_details"] or "[]"),
                "graph_paths_count": row["graph_paths_count"],
                "evidence_ids": json.loads(row["evidence_ids"] or "[]"),
                "llm_provider": row["llm_provider"],
                "validation_status": row["validation_status"],
                "confidence_score": row["confidence_score"],
                "confidence_level": row["confidence_level"],
                "recommendation": row["recommendation"],
                "requires_human_review": bool(row["requires_human_review"]),
                "action_id": row["action_id"],
                "action_status": row["action_status"]
            }

    def update_action_status(self, action_id: str, new_status: ActionStatus):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE audit_logs SET action_status = ? WHERE action_id = ?", (new_status.value, action_id))
            conn.commit()


audit_service = AuditService()
