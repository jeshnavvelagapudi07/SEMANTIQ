"""
Pydantic Schemas for Domain Models, Requests, Responses, and Reasoning Traces
"""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClassificationLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATIONS_ENGINEER = "operations_engineer"
    PROJECT_MANAGER = "project_manager"
    VIEWER = "viewer"


class EntityType(str, Enum):
    PROJECT = "project"
    SYSTEM = "system"
    INCIDENT = "incident"
    TEAM = "team"
    EMPLOYEE = "employee"
    DOCUMENT = "document"
    POLICY = "policy"
    CUSTOMER = "customer"


class RelationType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    OWNED_BY = "OWNED_BY"
    AFFECTED_BY = "AFFECTED_BY"
    RELATED_TO = "RELATED_TO"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    GOVERNED_BY = "GOVERNED_BY"
    ESCALATED_TO = "ESCALATED_TO"
    MAINTAINED_BY = "MAINTAINED_BY"
    IMPACTS = "IMPACTS"
    MEMBER_OF = "MEMBER_OF"


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QueryIntent(str, Enum):
    ENTITY_DESCRIPTION = "ENTITY_DESCRIPTION"
    DEPENDENCY_QUERY = "DEPENDENCY_QUERY"
    IMPACT_QUERY = "IMPACT_QUERY"
    INCIDENT_QUERY = "INCIDENT_QUERY"
    EVIDENCE_QUERY = "EVIDENCE_QUERY"
    POLICY_QUERY = "POLICY_QUERY"
    OWNERSHIP_QUERY = "OWNERSHIP_QUERY"
    RESTRICTED_QUERY = "RESTRICTED_QUERY"
    GENERAL_KNOWLEDGE_QUERY = "GENERAL_KNOWLEDGE_QUERY"


class ClaimSupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"             # Direct documentary evidence verified
    GRAPH_VERIFIED = "GRAPH_VERIFIED"   # Verified in knowledge graph, no documentary text chunk
    INFERRED = "INFERRED"               # Multi-hop inference
    UNSUPPORTED = "UNSUPPORTED"         # Citation failed or fact contradicts context
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# Core Knowledge Graph Models
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    id: str
    name: str
    type: EntityType
    description: str
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    owner_team: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    description: Optional[str] = None
    weight: float = 1.0


class Document(BaseModel):
    id: str
    title: str
    doc_type: str  # e.g., "SOP", "Specification", "Maintenance Log", "Contract", "Policy"
    content: str
    entity_ids: list[str] = Field(default_factory=list)
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    owner_team: Optional[str] = None
    version: str = "1.0"
    created_at: str = "2026-01-15"


class EvidenceChunk(BaseModel):
    id: str
    doc_id: str
    doc_title: str
    doc_type: str
    excerpt: str
    relevant_entities: list[str] = Field(default_factory=list)
    supported_relationships: list[str] = Field(default_factory=list)  # e.g. ["PRJ-DELTA:DEPENDS_ON:SYS-FURN-05"]
    classification: ClassificationLevel
    relevance_score: float = 0.0
    source_type: str = "Document"  # "Document", "SOP", "Policy", "MaintenanceLog"


class GraphPath(BaseModel):
    path_nodes: list[str]  # e.g. ["PRJ-GAMMA", "SYS-CNC-07", "INC-104", "SOP-017"]
    path_relationships: list[str]  # e.g. ["DEPENDS_ON", "AFFECTED_BY", "RELATED_TO"]
    description: str
    length: int
    score: float = 1.0


# ---------------------------------------------------------------------------
# Reasoning & LLM Output Models
# ---------------------------------------------------------------------------

class Claim(BaseModel):
    text: str
    entities: list[str] = Field(default_factory=list)
    relationship: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    support_status: ClaimSupportStatus = ClaimSupportStatus.SUPPORTED
    is_verified: bool = True  # True ONLY if support_status == SUPPORTED
    unsupported_reason: Optional[str] = None


class StructuredLLMOutput(BaseModel):
    answer: str
    recommendation: Optional[str] = None
    claims: list[Claim] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    suggested_action: Optional[str] = None


class DecisionFactor(BaseModel):
    factor: str
    impact: str  # "POSITIVE", "NEUTRAL", "NEGATIVE"
    details: str


class ConfidenceScore(BaseModel):
    score: float  # 0.0 to 100.0
    level: ConfidenceLevel
    explanation: str
    breakdown: dict[str, float] = Field(default_factory=dict)
    decision_factors: list[DecisionFactor] = Field(default_factory=list)


class FilteredItemSummary(BaseModel):
    entity_id: str
    entity_name: str
    classification: ClassificationLevel
    reason: str


class ReasoningTrace(BaseModel):
    query_intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY
    identified_entities: list[str]
    authorized_entities: list[str]
    filtered_entities_count: int
    filtered_details: list[FilteredItemSummary] = Field(default_factory=list)
    traversed_paths: list[GraphPath] = Field(default_factory=list)
    graph_facts: list[str] = Field(default_factory=list)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    decision_factors: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    confidence: ConfidenceScore
    minimized_context_token_estimate: int = 0


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    role: UserRole = UserRole.OPERATIONS_ENGINEER
    user_id: str = "usr_eng_01"
    max_hops: int = 3


class ActionItem(BaseModel):
    id: str
    query_id: str
    title: str
    description: str
    target_entity: str
    status: ActionStatus = ActionStatus.PENDING
    created_at: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    resolution_comment: Optional[str] = None


class QueryResponse(BaseModel):
    query_id: str
    user_role: UserRole
    user_id: str
    query: str
    query_intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY
    answer: str
    recommendation: Optional[str] = None
    claims: list[Claim] = Field(default_factory=list)
    # Claims that failed citation validation — excluded from grounded synthesis.
    # These may be presented to the user as unsupported inferences only.
    unsupported_claims: list[Claim] = Field(default_factory=list)
    graph_paths: list[GraphPath] = Field(default_factory=list)
    graph_facts: list[str] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)
    confidence: ConfidenceScore
    reasoning_trace: ReasoningTrace
    requires_human_review: bool = False
    action_item: Optional[ActionItem] = None
    filtered_items_count: int = 0
    filtered_summary: list[FilteredItemSummary] = Field(default_factory=list)
    provider_used: str  # "Gemini (gemini-2.0-flash)" or "Demo Mode (Simulated AI)"
    is_insufficient_evidence: bool = False
    missing_information: Optional[list[str]] = None


class ActionDecisionRequest(BaseModel):
    user_id: str = "usr_approver_01"
    comment: Optional[str] = None


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_role: UserRole
    query: str
    identified_entities: list[str]
    authorized_entities: list[str]
    filtered_entities_count: int
    graph_paths_count: int
    evidence_ids: list[str]
    llm_provider: str
    validation_status: str  # "PASSED", "WARNING", "FAILED"
    confidence_score: float
    confidence_level: str
    recommendation: Optional[str] = None
    requires_human_review: bool = False
    action_id: Optional[str] = None
    action_status: Optional[ActionStatus] = None


# ---------------------------------------------------------------------------
# Evaluation Models
# ---------------------------------------------------------------------------

class EvaluationTestCase(BaseModel):
    id: str
    name: str
    query: str
    role: UserRole
    expected_entities: list[str]
    expected_doc_ids: list[str]
    expected_path_nodes: Optional[list[str]] = None
    expected_insufficient: bool = False
    expected_filtered_docs: Optional[list[str]] = None
    category: str  # e.g., "Multi-Hop Reasoning", "Security Boundary", "Citation Grounding"


class EvaluationTestResult(BaseModel):
    test_id: str
    name: str
    category: str
    role: UserRole
    passed: bool
    latency_ms: float
    entity_accuracy: float
    path_accuracy: float
    citation_validity: float
    permission_leakage: bool
    structured_schema_valid: bool
    details: str


class EvaluationReport(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    avg_latency_ms: float
    entity_retrieval_accuracy: float
    graph_path_correctness: float
    citation_validity_rate: float
    permission_violation_rate: float
    unsupported_claim_rate: float
    structured_output_validity_rate: float
    timestamp: str
    test_results: list[EvaluationTestResult]
