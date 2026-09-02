import axios from 'axios';
import {
  UserRole,
  QueryResponse,
  AuditLogEntry,
  ActionItem,
  EvaluationReport,
  SystemHealth,
  Entity,
  EvidenceChunk,
  DocumentItem,
  AuthUser,
  AIStatus
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach cryptographic session token if present
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('semantiq_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Clear session on unauthorized 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      sessionStorage.removeItem('semantiq_token');
      sessionStorage.removeItem('semantiq_user');
    }
    return Promise.reject(error);
  }
);

export const semantiqApi = {
  // Authentication & Identity
  async login(credentials: string | { email?: string; username?: string; password?: string }): Promise<{
    token: string;
    user_id: string;
    employee_id?: string;
    username: string;
    email?: string;
    display_name: string;
    title: string;
    department?: string;
    role: UserRole;
    clearance_level?: string;
  }> {
    const payload = typeof credentials === 'string' ? { username: credentials } : credentials;
    const res = await apiClient.post('/auth/login', payload);
    if (res.data.token) {
      sessionStorage.setItem('semantiq_token', res.data.token);
      sessionStorage.setItem('semantiq_user', JSON.stringify(res.data));
    }
    return res.data;
  },

  async getMe(): Promise<AuthUser> {
    const res = await apiClient.get('/auth/me');
    return res.data;
  },

  async listDemoUsers(): Promise<{ count: number; users: AuthUser[] }> {
    const res = await apiClient.get('/auth/users');
    return res.data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      sessionStorage.removeItem('semantiq_token');
      sessionStorage.removeItem('semantiq_user');
    }
  },

  // System Health & AI Status
  async getHealth(): Promise<SystemHealth> {
    const res = await apiClient.get('/health');
    return res.data;
  },

  async getAIStatus(): Promise<AIStatus> {
    const res = await apiClient.get('/system/ai-status');
    return res.data;
  },

  // Knowledge Graph
  async getGraph(role?: UserRole): Promise<{ role: string; nodes: any[]; edges: any[]; stats: any }> {
    const res = await apiClient.get('/graph', { params: role ? { role } : {} });
    return res.data;
  },

  async getEntitySubgraph(entityId: string, role?: UserRole, hops: number = 2): Promise<any> {
    const res = await apiClient.get(`/graph/${entityId}`, { params: { ...(role ? { role } : {}), hops } });
    return res.data;
  },

  // Entities
  async listEntities(role?: UserRole, type?: string, search?: string): Promise<{ count: number; entities: Entity[] }> {
    const res = await apiClient.get('/entities', { params: { ...(role ? { role } : {}), type, search } });
    return res.data;
  },

  async getEntity(entityId: string, role?: UserRole): Promise<{ entity: Entity; connected_relationships: any[] }> {
    const res = await apiClient.get(`/entities/${entityId}`, { params: role ? { role } : {} });
    return res.data;
  },

  // Evidence
  async listEvidence(role?: UserRole, search?: string): Promise<{ count: number; evidence: EvidenceChunk[] }> {
    const res = await apiClient.get('/evidence', { params: { ...(role ? { role } : {}), search } });
    return res.data;
  },

  async getEvidenceDetail(evidenceId: string, role?: UserRole): Promise<{ evidence: EvidenceChunk; parent_document?: DocumentItem }> {
    const res = await apiClient.get(`/evidence/${evidenceId}`, { params: role ? { role } : {} });
    return res.data;
  },

  // Query Execution (Server-side resolved role overrides any body parameter)
  async executeQuery(query: string, role?: UserRole, maxHops: number = 3): Promise<QueryResponse> {
    const res = await apiClient.post('/query', {
      query,
      role,
      max_hops: maxHops,
    });
    return res.data;
  },

  async explainPath(sourceId: string, targetId: string, role?: UserRole): Promise<any> {
    const res = await apiClient.post('/query/explain-path', {
      source_id: sourceId,
      target_id: targetId,
      role,
    });
    return res.data;
  },

  // Security
  async getSecurityProfile(role?: UserRole): Promise<any> {
    const res = await apiClient.get('/security/me', { params: role ? { role } : {} });
    return res.data;
  },

  async getSecurityMatrix(): Promise<any> {
    const res = await apiClient.get('/security/matrix');
    return res.data;
  },

  async simulateSecurityCheck(role: UserRole, targetEntityIds: string[]): Promise<any> {
    const res = await apiClient.post('/security/simulate', {
      role,
      target_entity_ids: targetEntityIds,
    });
    return res.data;
  },

  // Audit Logs
  async getAuditLogs(limit: number = 50): Promise<{ count: number; logs: AuditLogEntry[] }> {
    const res = await apiClient.get('/audit', { params: { limit } });
    return res.data;
  },

  async getAuditLogDetail(queryId: string): Promise<any> {
    const res = await apiClient.get(`/audit/${queryId}`);
    return res.data;
  },

  // Actions
  async listActions(): Promise<{ count: number; actions: ActionItem[] }> {
    const res = await apiClient.get('/actions');
    return res.data;
  },

  async approveAction(actionId: string, comment?: string): Promise<ActionItem> {
    const res = await apiClient.post(`/actions/${actionId}/approve`, {
      user_id: 'usr_approver_01',
      comment: comment || 'Approved by authorized human operator.',
    });
    return res.data;
  },

  async rejectAction(actionId: string, comment?: string): Promise<ActionItem> {
    const res = await apiClient.post(`/actions/${actionId}/reject`, {
      user_id: 'usr_approver_01',
      comment: comment || 'Rejected by authorized human operator.',
    });
    return res.data;
  },

  // Admin User Management
  async listEmployees(): Promise<{ count: number; users: any[] }> {
    const res = await apiClient.get('/admin/users');
    return res.data;
  },

  async inviteEmployee(data: {
    email: string;
    display_name: string;
    department: string;
    job_title: string;
    role: UserRole;
    clearance_level: string;
    initial_password: string;
    employee_id?: string;
  }): Promise<{ status: string; message: string; user: any }> {
    const res = await apiClient.post('/admin/users/invite', data);
    return res.data;
  },

  async changeUserRole(userId: string, role: UserRole, reason?: string): Promise<{ status: string; message: string; user: any }> {
    const res = await apiClient.patch(`/admin/users/${userId}/role`, { role, reason });
    return res.data;
  },

  async changeUserClearance(userId: string, clearanceLevel: string, reason?: string): Promise<{ status: string; message: string; user: any }> {
    const res = await apiClient.patch(`/admin/users/${userId}/clearance`, { clearance_level: clearanceLevel, reason });
    return res.data;
  },

  async changeUserStatus(userId: string, status: 'ACTIVE' | 'DISABLED', reason?: string): Promise<{ status: string; message: string; user: any }> {
    const res = await apiClient.patch(`/admin/users/${userId}/status`, { status, reason });
    return res.data;
  },

  // Knowledge Management
  async listManagedEntities(status?: string, type?: string): Promise<{ count: number; entities: any[] }> {
    const res = await apiClient.get('/knowledge/entities', { params: { status, type } });
    return res.data;
  },

  async createEntity(data: {
    id: string;
    type: string;
    name: string;
    description: string;
    access_tier: string;
    owner_team?: string;
    properties?: Record<string, any>;
  }): Promise<{ status: string; entity: any }> {
    const res = await apiClient.post('/knowledge/entities', data);
    return res.data;
  },

  async updateEntity(entityId: string, data: {
    version: number;
    name?: string;
    description?: string;
    access_tier?: string;
    owner_team?: string;
    properties?: Record<string, any>;
  }): Promise<{ status: string; entity: any }> {
    const res = await apiClient.patch(`/knowledge/entities/${entityId}`, data);
    return res.data;
  },

  async archiveEntity(entityId: string, reason?: string): Promise<{ status: string; entity: any }> {
    const res = await apiClient.post(`/knowledge/entities/${entityId}/archive`, { reason });
    return res.data;
  },

  async listManagedRelationships(status?: string): Promise<{ count: number; relationships: any[] }> {
    const res = await apiClient.get('/knowledge/relationships', { params: { status } });
    return res.data;
  },

  async createRelationship(data: {
    source_entity_id: string;
    relationship_type: string;
    target_entity_id: string;
    evidence_ids?: string[];
    description?: string;
    access_tier?: string;
  }): Promise<{ status: string; relationship: any }> {
    const res = await apiClient.post('/knowledge/relationships', data);
    return res.data;
  },

  async listPendingRelationships(): Promise<{ count: number; relationships: any[] }> {
    const res = await apiClient.get('/knowledge/relationships/pending');
    return res.data;
  },

  async verifyRelationship(relId: string, comment?: string): Promise<{ status: string; relationship: any }> {
    const res = await apiClient.post(`/knowledge/relationships/${relId}/verify`, { comment });
    return res.data;
  },

  async rejectRelationship(relId: string, comment?: string): Promise<{ status: string; relationship: any }> {
    const res = await apiClient.post(`/knowledge/relationships/${relId}/reject`, { comment });
    return res.data;
  },

  async getChangeAuditLogs(limit: number = 50): Promise<{ count: number; changes: any[] }> {
    const res = await apiClient.get('/knowledge/changes', { params: { limit } });
    return res.data;
  },

  // Evaluation
  async getEvaluationReport(): Promise<EvaluationReport> {
    const res = await apiClient.get('/evaluation');
    return res.data;
  },

  async triggerEvaluationRun(): Promise<EvaluationReport> {
    const res = await apiClient.post('/evaluation/run');
    return res.data;
  },
};

