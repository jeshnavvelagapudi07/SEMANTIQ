export type UserRole = 'admin' | 'operations_engineer' | 'project_manager' | 'viewer';

export type ClassificationLevel = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED';

export type EntityType = 'project' | 'system' | 'incident' | 'team' | 'employee' | 'document' | 'policy' | 'customer';

export type RelationType = 
  | 'DEPENDS_ON' 
  | 'USES' 
  | 'OWNED_BY' 
  | 'AFFECTED_BY' 
  | 'RELATED_TO' 
  | 'DOCUMENTED_BY' 
  | 'GOVERNED_BY' 
  | 'ESCALATED_TO' 
  | 'MAINTAINED_BY' 
  | 'IMPACTS' 
  | 'MEMBER_OF';

export type ActionStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type ClaimSupportStatus = 'SUPPORTED' | 'GRAPH_VERIFIED' | 'INFERRED' | 'UNSUPPORTED' | 'INSUFFICIENT_EVIDENCE';

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description: string;
  classification: ClassificationLevel;
  owner_team?: string;
  properties: Record<string, any>;
}

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: RelationType;
  description?: string;
  weight: number;
}

export interface GraphNode {
  id: string;
  name: string;
  type: EntityType;
  classification: ClassificationLevel;
  description: string;
  owner_team?: string;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation_type: RelationType;
  description?: string;
  weight: number;
}

export interface DocumentItem {
  id: string;
  title: string;
  doc_type: string;
  content: string;
  entity_ids: string[];
  classification: ClassificationLevel;
  owner_team?: string;
  version: string;
  created_at: string;
}

export interface EvidenceChunk {
  id: string;
  doc_id: string;
  doc_title: string;
  doc_type: string;
  excerpt: string;
  relevant_entities: string[];
  classification: ClassificationLevel;
  relevance_score: number;
  source_type: string;
}

export interface GraphPath {
  path_nodes: string[];
  path_relationships: string[];
  description: string;
  length: number;
  score: number;
}

export interface Claim {
  text: string;
  entities?: string[];
  relationship?: string;
  evidence_ids: string[];
  support_status?: ClaimSupportStatus;
  is_verified: boolean;
  unsupported_reason?: string;
}

export interface DecisionFactor {
  factor: string;
  impact: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  details: string;
}

export interface ConfidenceScore {
  score: number;
  level: ConfidenceLevel;
  explanation: string;
  breakdown: Record<string, number>;
  decision_factors: DecisionFactor[];
}

export interface FilteredItemSummary {
  entity_id: string;
  entity_name: string;
  classification: ClassificationLevel;
  reason: string;
}

export interface ReasoningTrace {
  query_intent?: string;
  identified_entities: string[];
  authorized_entities: string[];
  filtered_entities_count: number;
  filtered_details: FilteredItemSummary[];
  traversed_paths: GraphPath[];
  graph_facts?: string[];
  retrieved_evidence_ids: string[];
  decision_factors: string[];
  validation_checks: string[];
  confidence: ConfidenceScore;
  minimized_context_token_estimate: number;
}

export interface ActionItem {
  id: string;
  query_id: string;
  title: string;
  description: string;
  target_entity: string;
  status: ActionStatus;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  resolution_comment?: string;
}

export interface QueryResponse {
  query_id: string;
  user_role: UserRole;
  user_id: string;
  query: string;
  query_intent?: string;
  answer: string;
  recommendation?: string;
  claims: Claim[];
  /** Claims that failed citation validation. Excluded from grounded synthesis. */
  unsupported_claims: Claim[];
  graph_paths: GraphPath[];
  graph_facts?: string[];
  evidence: EvidenceChunk[];
  confidence: ConfidenceScore;
  reasoning_trace: ReasoningTrace;
  requires_human_review: boolean;
  action_item?: ActionItem;
  filtered_items_count: number;
  filtered_summary: FilteredItemSummary[];
  provider_used: string;
  is_insufficient_evidence: boolean;
  missing_information?: string[];
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id: string;
  user_role: UserRole;
  query: string;
  identified_entities: string[];
  authorized_entities: string[];
  filtered_entities_count: number;
  graph_paths_count: number;
  evidence_ids: string[];
  llm_provider: string;
  validation_status: string;
  confidence_score: number;
  confidence_level: string;
  recommendation?: string;
  requires_human_review: boolean;
  action_id?: string;
  action_status?: ActionStatus;
}

export interface SystemHealth {
  status: string;
  system: string;
  version: string;
  tagline: string;
  ai_provider: string;
  is_gemini_configured: boolean;
  knowledge_graph: {
    nodes: number;
    edges: number;
    entity_types: Record<string, number>;
  };
}

export interface EvaluationTestResult {
  test_id: string;
  name: string;
  category: string;
  role: UserRole;
  passed: boolean;
  latency_ms: number;
  entity_accuracy: number;
  path_accuracy: number;
  citation_validity: number;
  permission_leakage: boolean;
  structured_schema_valid: boolean;
  details: string;
}

export interface EvaluationReport {
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  pass_rate: number;
  avg_latency_ms: number;
  entity_retrieval_accuracy: number;
  graph_path_correctness: number;
  citation_validity_rate: number;
  permission_violation_rate: number;
  unsupported_claim_rate: number;
  structured_output_validity_rate: number;
  timestamp: string;
  test_results: EvaluationTestResult[];
}

export interface AuthUser {
  user_id: string;
  username: string;
  email?: string;
  employee_id?: string;
  display_name: string;
  title: string;
  department?: string;
  role: UserRole;
  clearance_level?: string;
  active?: boolean;
}

export interface UserProfile {
  id: string;
  employee_id: string;
  username: string;
  email: string;
  display_name: string;
  department: string;
  job_title: string;
  role: UserRole;
  clearance_level: ClassificationLevel;
  status: 'ACTIVE' | 'DISABLED' | 'INVITED';
  created_at: string;
  updated_at: string;
}

export type EntityStatus = 'ACTIVE' | 'ARCHIVED' | 'SUPERSEDED';

export interface ManagedEntity {
  id: string;
  type: EntityType;
  name: string;
  description: string;
  access_tier: ClassificationLevel;
  status: EntityStatus;
  owner_team?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  version: number;
  properties: Record<string, any>;
}

export type RelationshipLifecycleStatus = 'PENDING_VERIFICATION' | 'VERIFIED' | 'REJECTED' | 'ARCHIVED';

export interface ManagedRelationship {
  id: string;
  source_entity_id: string;
  relationship_type: RelationType;
  target_entity_id: string;
  created_by: string;
  created_at: string;
  status: RelationshipLifecycleStatus;
  access_tier: ClassificationLevel;
  evidence_ids: string[];
  version: number;
  reviewed_by?: string;
  reviewed_at?: string;
  review_comment?: string;
  weight: number;
  description?: string;
}

export interface ChangeAuditEntry {
  id: string;
  timestamp: string;
  actor_user_id: string;
  actor_role: string;
  action_type: string;
  target_id: string;
  target_type: string;
  old_values?: string;
  new_values?: string;
  reason?: string;
}

export interface AIStatus {
  provider: string;
  configured: boolean;
  available: boolean;
  model: string;
  /** Possible values: 'live' | 'unconfigured' | 'quota_error' | 'authentication_error' |
   *  'model_error' | 'service_unavailable' | 'timeout' | 'network_error' | 'api_error' | 'invalid_response' */
  status: string;
}

