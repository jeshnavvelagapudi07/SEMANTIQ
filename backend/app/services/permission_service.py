"""
Permission and Access Control Service
Enforces zero-leakage, least-privilege filtering BEFORE graph traversal and LLM context creation.
"""
from typing import Optional
from app.models.schemas import (
    UserRole,
    ClassificationLevel,
    Entity,
    Document,
    EvidenceChunk,
    FilteredItemSummary
)

# Role-to-Classification Clearance Matrix
ROLE_CLEARANCE: dict[UserRole, set[ClassificationLevel]] = {
    UserRole.ADMIN: {
        ClassificationLevel.PUBLIC,
        ClassificationLevel.INTERNAL,
        ClassificationLevel.CONFIDENTIAL,
        ClassificationLevel.RESTRICTED
    },
    UserRole.OPERATIONS_ENGINEER: {
        ClassificationLevel.PUBLIC,
        ClassificationLevel.INTERNAL,
        ClassificationLevel.CONFIDENTIAL
    },
    UserRole.PROJECT_MANAGER: {
        ClassificationLevel.PUBLIC,
        ClassificationLevel.INTERNAL,
        ClassificationLevel.CONFIDENTIAL
    },
    UserRole.VIEWER: {
        ClassificationLevel.PUBLIC,
        ClassificationLevel.INTERNAL
    }
}


class PermissionService:
    """
    Zero-Trust Permission Gate.
    Guarantees that unauthorized records are filtered out BEFORE reaching
    the graph traversal, document retrieval, or LLM reasoning layers.
    """

    @staticmethod
    def is_authorized(role: UserRole, classification: ClassificationLevel) -> bool:
        """Checks if a user role has clearance to view an item of given classification."""
        allowed_tiers = ROLE_CLEARANCE.get(role, {ClassificationLevel.PUBLIC})
        return classification in allowed_tiers

    @classmethod
    def filter_entities(
        cls,
        role: UserRole,
        entities: list[Entity]
    ) -> tuple[list[Entity], list[FilteredItemSummary]]:
        """
        Filters a list of entities down to only those authorized for the role.
        Returns (authorized_entities, filtered_summaries).
        """
        authorized: list[Entity] = []
        filtered: list[FilteredItemSummary] = []

        for entity in entities:
            if cls.is_authorized(role, entity.classification):
                authorized.append(entity)
            else:
                filtered.append(FilteredItemSummary(
                    entity_id=entity.id,
                    entity_name=entity.name,
                    classification=entity.classification,
                    reason=f"Role '{role.value}' lacks clearance for {entity.classification.value} entity."
                ))

        return authorized, filtered

    @classmethod
    def filter_documents(
        cls,
        role: UserRole,
        documents: list[Document]
    ) -> tuple[list[Document], list[FilteredItemSummary]]:
        """
        Filters documents based on role clearance.
        """
        authorized: list[Document] = []
        filtered: list[FilteredItemSummary] = []

        for doc in documents:
            if cls.is_authorized(role, doc.classification):
                authorized.append(doc)
            else:
                filtered.append(FilteredItemSummary(
                    entity_id=doc.id,
                    entity_name=doc.title,
                    classification=doc.classification,
                    reason=f"Role '{role.value}' lacks clearance for {doc.classification.value} document '{doc.id}'."
                ))

        return authorized, filtered

    @classmethod
    def filter_evidence(
        cls,
        role: UserRole,
        evidence_chunks: list[EvidenceChunk]
    ) -> tuple[list[EvidenceChunk], list[FilteredItemSummary]]:
        """
        Filters evidence chunks based on role clearance.
        """
        authorized: list[EvidenceChunk] = []
        filtered: list[FilteredItemSummary] = []

        for ev in evidence_chunks:
            if cls.is_authorized(role, ev.classification):
                authorized.append(ev)
            else:
                filtered.append(FilteredItemSummary(
                    entity_id=ev.id,
                    entity_name=f"Evidence from {ev.doc_title}",
                    classification=ev.classification,
                    reason=f"Role '{role.value}' lacks clearance for {ev.classification.value} evidence chunk '{ev.id}'."
                ))

        return authorized, filtered

    @classmethod
    def get_security_matrix(cls) -> dict[str, list[str]]:
        """Returns the full permission matrix for UI and Security views."""
        return {
            role.value: [lvl.value for lvl in levels]
            for role, levels in ROLE_CLEARANCE.items()
        }


permission_service = PermissionService()
