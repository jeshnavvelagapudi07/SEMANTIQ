"""
Knowledge Management Service
Enforces strict role-based entity creation, optimistic version locking, relationship integrity,
provenance tracking, human-in-the-loop relationship verification, and change audit logging.
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from app.core.database import get_db_connection
from app.models.schemas import (
    UserRole,
    ClassificationLevel,
    EntityType,
    RelationType,
    Entity,
    Relationship
)
from app.services.permission_service import permission_service
from app.services.graph_service import graph_service


class KnowledgeService:
    @staticmethod
    def list_entities(role: UserRole, status: Optional[str] = "ACTIVE", entity_type: Optional[str] = None) -> list[dict]:
        """Lists entities accessible under user clearance, filtering by lifecycle status and type."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM entities WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status.upper())
            if entity_type:
                query += " AND LOWER(type) = LOWER(?)"
                params.append(entity_type)

            query += " ORDER BY name ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                item = dict(r)
                # Parse metadata JSON
                if item.get("metadata"):
                    try:
                        item["properties"] = json.loads(item["metadata"])
                    except Exception:
                        item["properties"] = {}
                else:
                    item["properties"] = {}

                # Filter by clearance
                try:
                    cls_level = ClassificationLevel(item["access_tier"])
                    if permission_service.is_authorized(role, cls_level):
                        results.append(item)
                except ValueError:
                    results.append(item)

            return results

    @staticmethod
    def get_entity_by_id(entity_id: str) -> Optional[dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                item = dict(row)
                item["properties"] = json.loads(item["metadata"]) if item.get("metadata") else {}
                return item
        return None

    @staticmethod
    def create_entity(
        creator_id: str,
        creator_role: UserRole,
        entity_id: str,
        entity_type: str,
        name: str,
        description: str,
        access_tier: ClassificationLevel,
        owner_team: Optional[str] = None,
        properties: Optional[dict] = None
    ) -> dict:
        """
        Creates a new knowledge entity with strict role-based type & clearance validation.
        Audits creation.
        """
        # Rule 1: Viewer cannot create entities
        if creator_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers have read-only permissions.")

        # Rule 2: Employee records must originate from User Management
        norm_type = entity_type.strip().lower()
        if norm_type == "employee":
            raise HTTPException(
                status_code=400,
                detail="Employee entities cannot be created manually. They must be provisioned through User Management."
            )

        # Validate entity type against allowed enum
        try:
            valid_type = EntityType(norm_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity type '{entity_type}'. Allowed types: PROJECT, SYSTEM, TEAM, INCIDENT, DOCUMENT, SOP, POLICY."
            )

        # Rule 3: Role-based entity type scope
        if creator_role == UserRole.PROJECT_MANAGER:
            if valid_type not in (EntityType.PROJECT, EntityType.DOCUMENT, EntityType.POLICY, EntityType.TEAM):
                raise HTTPException(
                    status_code=403,
                    detail=f"Project Managers can only create Project, Document, Policy, or Team entities."
                )
        elif creator_role == UserRole.OPERATIONS_ENGINEER:
            if valid_type not in (EntityType.SYSTEM, EntityType.INCIDENT, EntityType.DOCUMENT, EntityType.TEAM):
                raise HTTPException(
                    status_code=403,
                    detail=f"Operations Engineers can only create System, Incident, Document/SOP, or Team entities."
                )

        # Rule 4: Clearance tier check (cannot create entities higher than user's clearance)
        if not permission_service.is_authorized(creator_role, access_tier):
            raise HTTPException(
                status_code=403,
                detail=f"Clearance mismatch: User role '{creator_role.value}' cannot create '{access_tier.value}' classified assets."
            )

        # Check for ID duplicate
        if KnowledgeService.get_entity_by_id(entity_id):
            raise HTTPException(status_code=400, detail=f"Entity with ID '{entity_id}' already exists.")

        now = datetime.now(timezone.utc).isoformat()
        props = properties or {}

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entities (
                    id, type, name, description, metadata, access_tier,
                    status, owner_team, created_by, created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_id, valid_type.value, name, description,
                json.dumps(props), access_tier.value, "ACTIVE",
                owner_team, creator_id, now, now, 1
            ))

            # Record change audit
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, creator_id, creator_role.value, "ENTITY_CREATE",
                entity_id, "ENTITY", None,
                json.dumps({
                    "name": name,
                    "type": valid_type.value,
                    "access_tier": access_tier.value,
                    "owner_team": owner_team
                }),
                f"Entity '{name}' ({entity_id}) created by {creator_id}."
            ))
            conn.commit()

        # Update in-memory graph service
        new_ent = Entity(
            id=entity_id,
            name=name,
            type=valid_type,
            description=description,
            classification=access_tier,
            owner_team=owner_team,
            properties=props
        )
        graph_service.entities_by_id[entity_id] = new_ent
        graph_service.graph.add_node(
            entity_id,
            name=name,
            type=valid_type.value,
            classification=access_tier.value,
            description=description,
            owner_team=owner_team,
            properties=props
        )

        return KnowledgeService.get_entity_by_id(entity_id)

    @staticmethod
    def update_entity(
        updater_id: str,
        updater_role: UserRole,
        entity_id: str,
        expected_version: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        access_tier: Optional[ClassificationLevel] = None,
        owner_team: Optional[str] = None,
        properties: Optional[dict] = None
    ) -> dict:
        """Updates entity with optimistic version locking to prevent concurrent overwrite."""
        if updater_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers have read-only permissions.")

        existing = KnowledgeService.get_entity_by_id(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Entity not found.")

        # Optimistic Locking check
        if existing["version"] != expected_version:
            raise HTTPException(
                status_code=409,
                detail=f"Version conflict: Entity was modified by another user (current version: {existing['version']}, expected: {expected_version}). Please refresh and retry."
            )

        new_name = name if name is not None else existing["name"]
        new_desc = description if description is not None else existing["description"]
        new_tier = access_tier.value if access_tier is not None else existing["access_tier"]
        new_owner = owner_team if owner_team is not None else existing["owner_team"]
        new_props = properties if properties is not None else existing["properties"]
        new_version = existing["version"] + 1
        now = datetime.now(timezone.utc).isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE entities SET
                    name = ?, description = ?, metadata = ?, access_tier = ?,
                    owner_team = ?, updated_at = ?, version = ?
                WHERE id = ? AND version = ?
            """, (
                new_name, new_desc, json.dumps(new_props), new_tier,
                new_owner, now, new_version, entity_id, expected_version
            ))

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=409,
                    detail="Concurrent modification conflict: Failed to commit entity update. Please refresh."
                )

            # Audit change
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, updater_id, updater_role.value, "ENTITY_UPDATE",
                entity_id, "ENTITY",
                json.dumps({"name": existing["name"], "version": existing["version"], "access_tier": existing["access_tier"]}),
                json.dumps({"name": new_name, "version": new_version, "access_tier": new_tier}),
                f"Entity {entity_id} updated from v{existing['version']} to v{new_version}."
            ))
            conn.commit()

        # Update in-memory graph service
        if entity_id in graph_service.entities_by_id:
            ent = graph_service.entities_by_id[entity_id]
            ent.name = new_name
            ent.description = new_desc
            ent.classification = ClassificationLevel(new_tier)
            ent.owner_team = new_owner
            ent.properties = new_props
            if graph_service.graph.has_node(entity_id):
                graph_service.graph.nodes[entity_id].update({
                    "name": new_name,
                    "description": new_desc,
                    "classification": new_tier,
                    "owner_team": new_owner,
                    "properties": new_props
                })

        return KnowledgeService.get_entity_by_id(entity_id)

    @staticmethod
    def archive_entity(actor_id: str, actor_role: UserRole, entity_id: str, reason: Optional[str] = None) -> dict:
        """Transitions entity to ARCHIVED status instead of destructive hard delete."""
        if actor_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers cannot archive entities.")

        existing = KnowledgeService.get_entity_by_id(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Entity not found.")

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE entities SET status = 'ARCHIVED', updated_at = ? WHERE id = ?", (now, entity_id))

            # Audit log
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, actor_id, actor_role.value, "ENTITY_ARCHIVE",
                entity_id, "ENTITY",
                json.dumps({"status": existing["status"]}),
                json.dumps({"status": "ARCHIVED"}),
                reason or f"Entity archived by {actor_id}."
            ))
            conn.commit()

        # Prune from in-memory operational graph (historical audit records preserved)
        if graph_service.graph.has_node(entity_id):
            graph_service.graph.remove_node(entity_id)
        if entity_id in graph_service.entities_by_id:
            del graph_service.entities_by_id[entity_id]

        return KnowledgeService.get_entity_by_id(entity_id)

    # ──────────────────────────────────────────────────────────────────────────
    # Relationship Management & Human Verification
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def list_relationships(role: UserRole, status: Optional[str] = None) -> list[dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM relationships WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status.upper())
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                item = dict(r)
                item["evidence_ids"] = json.loads(item["evidence_ids"]) if item.get("evidence_ids") else []
                # Clearance check
                try:
                    cls_level = ClassificationLevel(item.get("access_tier", "INTERNAL"))
                    if permission_service.is_authorized(role, cls_level):
                        results.append(item)
                except ValueError:
                    results.append(item)
            return results

    @staticmethod
    def get_relationship_by_id(rel_id: str) -> Optional[dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM relationships WHERE id = ?", (rel_id,))
            row = cursor.fetchone()
            if row:
                item = dict(row)
                item["evidence_ids"] = json.loads(item["evidence_ids"]) if item.get("evidence_ids") else []
                return item
        return None

    @staticmethod
    def create_relationship(
        creator_id: str,
        creator_role: UserRole,
        source_id: str,
        relationship_type: str,
        target_id: str,
        evidence_ids: Optional[list[str]] = None,
        description: Optional[str] = None,
        access_tier: Optional[ClassificationLevel] = None
    ) -> dict:
        """
        Proposes a new knowledge graph relationship.
        Enforces integrity: source/target existence, prohibited self-loops, duplicate avoidance,
        and starts in PENDING_VERIFICATION unless created by Administrator.
        """
        # Rule 1: Viewer cannot create relationships
        if creator_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers cannot create relationships.")

        # Rule 2: Prohibited self-loop
        if source_id.strip().upper() == target_id.strip().upper():
            raise HTTPException(status_code=400, detail="Relationship integrity violation: Self-referencing loops are prohibited.")

        # Rule 3: Validate relationship type
        try:
            rel_enum = RelationType(relationship_type.strip().upper())
        except ValueError:
            allowed = ", ".join([r.value for r in RelationType])
            raise HTTPException(status_code=400, detail=f"Invalid relationship type '{relationship_type}'. Allowed: {allowed}")

        # Rule 4: Verify source and target existence and active status
        source_ent = KnowledgeService.get_entity_by_id(source_id)
        if not source_ent:
            raise HTTPException(status_code=400, detail=f"Source entity '{source_id}' does not exist in knowledge repository.")
        if source_ent["status"] != "ACTIVE":
            raise HTTPException(status_code=400, detail=f"Source entity '{source_id}' is {source_ent['status']} and cannot receive new connections.")

        target_ent = KnowledgeService.get_entity_by_id(target_id)
        if not target_ent:
            raise HTTPException(status_code=400, detail=f"Target entity '{target_id}' does not exist in knowledge repository.")
        if target_ent["status"] != "ACTIVE":
            raise HTTPException(status_code=400, detail=f"Target entity '{target_id}' is {target_ent['status']} and cannot receive new connections.")

        # Rule 5: User must have clearance for both source and target entities
        source_cls = ClassificationLevel(source_ent["access_tier"])
        target_cls = ClassificationLevel(target_ent["access_tier"])
        if not permission_service.is_authorized(creator_role, source_cls) or not permission_service.is_authorized(creator_role, target_cls):
            raise HTTPException(status_code=403, detail="Access denied: Creator clearance is insufficient for one or more connected entities.")

        tier = access_tier or max([source_cls, target_cls], key=lambda c: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"].index(c.value))
        if not permission_service.is_authorized(creator_role, tier):
            raise HTTPException(status_code=403, detail="Access denied: Relationship access tier exceeds user clearance.")

        # Rule 6: Duplicate detection (prevent identical active edges)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM relationships
                WHERE source_entity_id = ? AND relationship_type = ? AND target_entity_id = ?
                  AND status IN ('ACTIVE', 'VERIFIED', 'PENDING_VERIFICATION')
            """, (source_id, rel_enum.value, target_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Duplicate relationship: An active or pending relationship between these entities already exists.")

        now = datetime.now(timezone.utc).isoformat()
        rel_id = f"REL-{source_id}-{rel_enum.value}-{target_id}"

        # Human Verification Policy: Admin creations can be immediately VERIFIED; non-admin are PENDING_VERIFICATION
        initial_status = "VERIFIED" if creator_role == UserRole.ADMIN else "PENDING_VERIFICATION"
        reviewed_by = creator_id if initial_status == "VERIFIED" else None
        reviewed_at = now if initial_status == "VERIFIED" else None
        review_comment = "Administrator-created authoritative relationship." if initial_status == "VERIFIED" else None

        ev_list = evidence_ids or []
        desc = description or f"{source_ent['name']} [{rel_enum.value}] {target_ent['name']}"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO relationships (
                    id, source_entity_id, relationship_type, target_entity_id,
                    created_by, created_at, status, access_tier, evidence_ids,
                    version, reviewed_by, reviewed_at, review_comment, weight, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rel_id, source_id, rel_enum.value, target_id,
                creator_id, now, initial_status, tier.value, json.dumps(ev_list),
                1, reviewed_by, reviewed_at, review_comment, 1.0, desc
            ))

            # Audit log entry
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, creator_id, creator_role.value, "RELATIONSHIP_CREATE",
                rel_id, "RELATIONSHIP", None,
                json.dumps({
                    "source": source_id,
                    "type": rel_enum.value,
                    "target": target_id,
                    "status": initial_status,
                    "access_tier": tier.value
                }),
                f"Relationship proposed by {creator_id}. Status: {initial_status}."
            ))
            conn.commit()

        # If immediately verified, activate in in-memory graph
        if initial_status == "VERIFIED":
            rel_obj = Relationship(
                id=rel_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_enum,
                description=desc,
                weight=1.0
            )
            graph_service.relationships_by_id[rel_id] = rel_obj
            graph_service.graph.add_edge(
                source_id, target_id,
                key=rel_id, id=rel_id,
                relation_type=rel_enum.value,
                description=desc, weight=1.0
            )

        return KnowledgeService.get_relationship_by_id(rel_id)

    @staticmethod
    def verify_relationship(
        reviewer_id: str,
        reviewer_role: UserRole,
        rel_id: str,
        comment: Optional[str] = None
    ) -> dict:
        """Human reviewer approves a pending relationship into the active authoritative graph."""
        if reviewer_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers cannot verify relationships.")

        rel = KnowledgeService.get_relationship_by_id(rel_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relationship not found.")

        if rel["status"] == "VERIFIED":
            return rel

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE relationships SET
                    status = 'VERIFIED', reviewed_by = ?, reviewed_at = ?, review_comment = ?, version = version + 1
                WHERE id = ?
            """, (reviewer_id, now, comment or "Approved by authorized human operator.", rel_id))

            # Audit
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, reviewer_id, reviewer_role.value, "RELATIONSHIP_VERIFY",
                rel_id, "RELATIONSHIP",
                json.dumps({"status": rel["status"]}),
                json.dumps({"status": "VERIFIED"}),
                comment or "Approved relationship for authoritative GraphRAG reasoning."
            ))
            conn.commit()

        # Activate in in-memory graph
        rel_enum = RelationType(rel["relationship_type"])
        rel_obj = Relationship(
            id=rel_id,
            source_id=rel["source_entity_id"],
            target_id=rel["target_entity_id"],
            relation_type=rel_enum,
            description=rel.get("description"),
            weight=rel.get("weight", 1.0)
        )
        graph_service.relationships_by_id[rel_id] = rel_obj
        graph_service.graph.add_edge(
            rel["source_entity_id"], rel["target_entity_id"],
            key=rel_id, id=rel_id,
            relation_type=rel_enum.value,
            description=rel.get("description"),
            weight=1.0
        )

        return KnowledgeService.get_relationship_by_id(rel_id)

    @staticmethod
    def reject_relationship(
        reviewer_id: str,
        reviewer_role: UserRole,
        rel_id: str,
        comment: Optional[str] = None
    ) -> dict:
        """Human reviewer rejects a proposed relationship."""
        if reviewer_role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Forbidden: Viewers cannot reject relationships.")

        rel = KnowledgeService.get_relationship_by_id(rel_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relationship not found.")

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE relationships SET
                    status = 'REJECTED', reviewed_by = ?, reviewed_at = ?, review_comment = ?, version = version + 1
                WHERE id = ?
            """, (reviewer_id, now, comment or "Rejected by human reviewer.", rel_id))

            # Audit
            log_id = f"CHG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO change_audit_logs (
                    id, timestamp, actor_user_id, actor_role, action_type,
                    target_id, target_type, old_values, new_values, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, now, reviewer_id, reviewer_role.value, "RELATIONSHIP_REJECT",
                rel_id, "RELATIONSHIP",
                json.dumps({"status": rel["status"]}),
                json.dumps({"status": "REJECTED"}),
                comment or "Relationship rejected."
            ))
            conn.commit()

        # Remove from active graph if it was previously there
        if graph_service.graph.has_edge(rel["source_entity_id"], rel["target_entity_id"], key=rel_id):
            graph_service.graph.remove_edge(rel["source_entity_id"], rel["target_entity_id"], key=rel_id)
        if rel_id in graph_service.relationships_by_id:
            del graph_service.relationships_by_id[rel_id]

        return KnowledgeService.get_relationship_by_id(rel_id)

    @staticmethod
    def get_change_audit_logs(limit: int = 100) -> list[dict]:
        """Retrieves recent entries from the change audit ledger."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM change_audit_logs ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


knowledge_service = KnowledgeService()
