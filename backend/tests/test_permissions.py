"""
Unit Tests for Permission Service
Validates role clearances, entity pre-filtering, and document isolation.
"""
import pytest
from app.models.schemas import (
    UserRole,
    ClassificationLevel,
    Entity,
    EntityType,
    Document
)
from app.services.permission_service import permission_service


def test_role_clearances():
    # Admin can access all
    assert permission_service.is_authorized(UserRole.ADMIN, ClassificationLevel.PUBLIC)
    assert permission_service.is_authorized(UserRole.ADMIN, ClassificationLevel.INTERNAL)
    assert permission_service.is_authorized(UserRole.ADMIN, ClassificationLevel.CONFIDENTIAL)
    assert permission_service.is_authorized(UserRole.ADMIN, ClassificationLevel.RESTRICTED)

    # Operations Engineer
    assert permission_service.is_authorized(UserRole.OPERATIONS_ENGINEER, ClassificationLevel.PUBLIC)
    assert permission_service.is_authorized(UserRole.OPERATIONS_ENGINEER, ClassificationLevel.INTERNAL)
    assert permission_service.is_authorized(UserRole.OPERATIONS_ENGINEER, ClassificationLevel.CONFIDENTIAL)
    assert not permission_service.is_authorized(UserRole.OPERATIONS_ENGINEER, ClassificationLevel.RESTRICTED)

    # Project Manager
    assert permission_service.is_authorized(UserRole.PROJECT_MANAGER, ClassificationLevel.PUBLIC)
    assert permission_service.is_authorized(UserRole.PROJECT_MANAGER, ClassificationLevel.INTERNAL)
    assert permission_service.is_authorized(UserRole.PROJECT_MANAGER, ClassificationLevel.CONFIDENTIAL)
    assert not permission_service.is_authorized(UserRole.PROJECT_MANAGER, ClassificationLevel.RESTRICTED)

    # Viewer
    assert permission_service.is_authorized(UserRole.VIEWER, ClassificationLevel.PUBLIC)
    assert permission_service.is_authorized(UserRole.VIEWER, ClassificationLevel.INTERNAL)
    assert not permission_service.is_authorized(UserRole.VIEWER, ClassificationLevel.CONFIDENTIAL)
    assert not permission_service.is_authorized(UserRole.VIEWER, ClassificationLevel.RESTRICTED)


def test_entity_filtering():
    entities = [
        Entity(id="E1", name="Public Roster", type=EntityType.TEAM, description="Public", classification=ClassificationLevel.PUBLIC),
        Entity(id="E2", name="CNC-07", type=EntityType.SYSTEM, description="Internal machine", classification=ClassificationLevel.INTERNAL),
        Entity(id="E3", name="SCADA Telemetry", type=EntityType.SYSTEM, description="Confidential SCADA", classification=ClassificationLevel.CONFIDENTIAL),
        Entity(id="E4", name="Master Contract", type=EntityType.CUSTOMER, description="Restricted Contract", classification=ClassificationLevel.RESTRICTED),
    ]

    # Viewer should only see Public + Internal
    auth_viewer, filtered_viewer = permission_service.filter_entities(UserRole.VIEWER, entities)
    assert [e.id for e in auth_viewer] == ["E1", "E2"]
    assert len(filtered_viewer) == 2
    assert {f.entity_id for f in filtered_viewer} == {"E3", "E4"}

    # Operations Engineer should see Public + Internal + Confidential
    auth_ops, filtered_ops = permission_service.filter_entities(UserRole.OPERATIONS_ENGINEER, entities)
    assert [e.id for e in auth_ops] == ["E1", "E2", "E3"]
    assert len(filtered_ops) == 1
    assert filtered_ops[0].entity_id == "E4"

    # Admin sees all 4
    auth_admin, filtered_admin = permission_service.filter_entities(UserRole.ADMIN, entities)
    assert len(auth_admin) == 4
    assert len(filtered_admin) == 0


def test_document_filtering():
    docs = [
        Document(id="D1", title="Public Safety", doc_type="Policy", content="...", classification=ClassificationLevel.PUBLIC),
        Document(id="D2", title="CNC SOP", doc_type="SOP", content="...", classification=ClassificationLevel.INTERNAL),
        Document(id="D3", title="Proprietary Toolpath", doc_type="Spec", content="...", classification=ClassificationLevel.CONFIDENTIAL),
        Document(id="D4", title="Executive Contract 22", doc_type="Contract", content="...", classification=ClassificationLevel.RESTRICTED),
    ]

    auth_pm, filtered_pm = permission_service.filter_documents(UserRole.PROJECT_MANAGER, docs)
    assert [d.id for d in auth_pm] == ["D1", "D2", "D3"]
    assert len(filtered_pm) == 1
    assert filtered_pm[0].entity_id == "D4"
