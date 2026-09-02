"""
Tests for Knowledge Graph Management, Entity/Relationship Lifecycle,
Integrity Constraints (Self-Loops, Duplicates, Non-Existent Nodes),
Optimistic Version Locking, Human-in-the-Loop Verification, and Change Auditing
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.auth import create_access_token
from app.services.graph_service import graph_service

@pytest.mark.asyncio
async def test_admin_creates_and_archives_entity():
    import uuid
    ent_id = f"SYS-CRYO-{uuid.uuid4().hex[:6].upper()}"
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin creates a new system entity
        create_res = await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": ent_id,
                "type": "system",
                "name": "Cryogenic Helium Recirculator 09",
                "description": "Closed-loop sub-Kelvin cooling unit for quantum sensor calibration.",
                "access_tier": "CONFIDENTIAL",
                "owner_team": "TEAM-RELIABILITY",
                "properties": {"pressure_bar": 4.2, "temp_kelvin": 3.8}
            }
        )
        assert create_res.status_code == 200
        ent = create_res.json()["entity"]
        assert ent["id"] == ent_id
        assert ent["status"] == "ACTIVE"
        assert ent["version"] == 1

        # Check graph service has node
        assert ent_id in graph_service.entities_by_id

        # 2. Soft-archive entity
        archive_res = await client.post(
            f"/api/knowledge/entities/{ent_id}/archive",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": "Decommissioned and replaced by SYS-CRYO-10"}
        )
        assert archive_res.status_code == 200
        archived_ent = archive_res.json()["entity"]
        assert archived_ent["status"] == "ARCHIVED"

        # Pruned from active operational graph
        assert ent_id not in graph_service.entities_by_id


@pytest.mark.asyncio
async def test_entity_optimistic_version_conflict():
    import uuid
    ent_id = f"SYS-PUMP-{uuid.uuid4().hex[:6].upper()}"
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create entity
        res = await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": ent_id,
                "type": "system",
                "name": "High-Pressure Hydraulic Pump 01",
                "description": "Primary pressure feed for Bay 4.",
                "access_tier": "INTERNAL"
            }
        )
        assert res.status_code == 200

        # Attempt update with WRONG version (e.g. version=99 instead of 1)
        conflict_res = await client.patch(
            f"/api/knowledge/entities/{ent_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "version": 99,
                "description": "Unauthorized overwrite attempt with stale version."
            }
        )
        assert conflict_res.status_code == 409
        assert "version conflict" in conflict_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_operations_engineer_entity_permissions_and_restrictions():
    import uuid
    inc_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    ops_token = create_access_token("ops_eng_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Allowed: Operations Engineer creates an INCIDENT
        inc_res = await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "id": inc_id,
                "type": "incident",
                "name": "Spindle Vibration Excursion on CNC-07",
                "description": "Harmonic resonance anomaly detected at 12,000 RPM.",
                "access_tier": "CONFIDENTIAL",
                "owner_team": "TEAM-MFG-OPS"
            }
        )
        assert inc_res.status_code == 200
        assert inc_res.json()["entity"]["id"] == inc_id

        # 2. Denied: Operations Engineer attempts to create a RESTRICTED entity (Contract)
        denied_res = await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "id": "DOC-SECRET-01",
                "type": "document",
                "name": "Merger Acquisition Agreement",
                "description": "Restricted commercial corporate document.",
                "access_tier": "RESTRICTED"
            }
        )
        assert denied_res.status_code == 403


@pytest.mark.asyncio
async def test_employee_entity_manual_creation_blocked():
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": "EMP-FAKE-99",
                "type": "employee",
                "name": "Fake Employee",
                "description": "Manual fake employee bypass.",
                "access_tier": "INTERNAL"
            }
        )
        assert res.status_code == 400
        assert "user management" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_relationship_integrity_validations():
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Self-referencing loop prohibited
        self_res = await client.post(
            "/api/knowledge/relationships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "source_entity_id": "SYS-CNC-07",
                "relationship_type": "DEPENDS_ON",
                "target_entity_id": "SYS-CNC-07"
            }
        )
        assert self_res.status_code == 400
        assert "self-referencing" in self_res.json()["detail"].lower()

        # 2. Non-existent source entity rejected
        missing_src = await client.post(
            "/api/knowledge/relationships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "source_entity_id": "SYS-NON-EXISTENT",
                "relationship_type": "DEPENDS_ON",
                "target_entity_id": "SYS-CNC-07"
            }
        )
        assert missing_src.status_code == 400
        assert "does not exist" in missing_src.json()["detail"].lower()

        # 3. Non-existent target entity rejected
        missing_tgt = await client.post(
            "/api/knowledge/relationships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "source_entity_id": "SYS-CNC-07",
                "relationship_type": "DEPENDS_ON",
                "target_entity_id": "SYS-GHOST-999"
            }
        )
        assert missing_tgt.status_code == 400
        assert "does not exist" in missing_tgt.json()["detail"].lower()


@pytest.mark.asyncio
async def test_human_verification_workflow_for_relationships():
    import uuid
    uid = uuid.uuid4().hex[:6].upper()
    robot_id = f"SYS-ROBOT-{uid}"
    plc_id = f"SYS-PLC-{uid}"
    ops_token = create_access_token("ops_eng_01")
    admin_token = create_access_token("admin_01")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. First ensure source and target entities exist
        await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": robot_id,
                "type": "system",
                "name": "Test Articulated Robot 01",
                "description": "Robotic test arm for palletizing.",
                "access_tier": "INTERNAL"
            }
        )
        await client.post(
            "/api/knowledge/entities",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "id": plc_id,
                "type": "system",
                "name": "Test PLC Controller 01",
                "description": "Programmable logic controller.",
                "access_tier": "INTERNAL"
            }
        )

        # 2. Operations Engineer proposes a relationship -> starts in PENDING_VERIFICATION
        rel_res = await client.post(
            "/api/knowledge/relationships",
            headers={"Authorization": f"Bearer {ops_token}"},
            json={
                "source_entity_id": robot_id,
                "relationship_type": "DEPENDS_ON",
                "target_entity_id": plc_id,
                "description": "Robot requires PLC heartbeat."
            }
        )
        assert rel_res.status_code == 200
        rel_data = rel_res.json()["relationship"]
        rel_id = rel_data["id"]
        assert rel_data["status"] == "PENDING_VERIFICATION"

        # 3. Assert pending relationship does NOT yet participate in active graph traversal
        assert not graph_service.graph.has_edge(robot_id, plc_id, key=rel_id)

        # 4. Reviewer approves relationship -> becomes VERIFIED and active in graph
        verify_res = await client.post(
            f"/api/knowledge/relationships/{rel_id}/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"comment": "Verified cabling schematic and PLC heartbeat."}
        )
        assert verify_res.status_code == 200
        verified_data = verify_res.json()["relationship"]
        assert verified_data["status"] == "VERIFIED"
        assert verified_data["reviewed_by"] == "usr_admin_01"

        # 5. Now active in graph traversal
        assert graph_service.graph.has_edge(robot_id, plc_id, key=rel_id)
