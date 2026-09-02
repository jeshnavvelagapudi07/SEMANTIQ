import React, { useState, useEffect } from 'react';
import { UserRole, ClassificationLevel, EntityType, RelationType, ManagedEntity, ManagedRelationship, ChangeAuditEntry } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  Layers,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Archive,
  ArrowRight,
  Shield,
  Activity,
  History,
  FileText,
  AlertCircle,
  Sparkles,
  GitBranch,
  RefreshCw,
  Eye,
  Check,
  X
} from 'lucide-react';

interface KnowledgeManagementViewProps {
  currentRole: UserRole;
  onRefreshGraph?: () => void;
}

type KmTab = 'entities' | 'relationships' | 'pending' | 'changes';

export const KnowledgeManagementView: React.FC<KnowledgeManagementViewProps> = ({
  currentRole,
  onRefreshGraph
}) => {
  const [activeTab, setActiveTab] = useState<KmTab>('entities');
  const [entities, setEntities] = useState<ManagedEntity[]>([]);
  const [relationships, setRelationships] = useState<ManagedRelationship[]>([]);
  const [pendingRelationships, setPendingRelationships] = useState<ManagedRelationship[]>([]);
  const [changeLogs, setChangeLogs] = useState<ChangeAuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [showCreateEntityModal, setShowCreateEntityModal] = useState(false);
  const [showCreateRelModal, setShowCreateRelModal] = useState(false);
  const [reviewModalRel, setReviewModalRel] = useState<ManagedRelationship | null>(null);
  const [reviewAction, setReviewAction] = useState<'verify' | 'reject'>('verify');
  const [reviewComment, setReviewComment] = useState('');

  // Filters
  const [entitySearch, setEntitySearch] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [entityStatusFilter, setEntityStatusFilter] = useState('ACTIVE');

  // Form states: Create Entity
  const [newEntityId, setNewEntityId] = useState('');
  const [newEntityType, setNewEntityType] = useState<EntityType>('system');
  const [newEntityName, setNewEntityName] = useState('');
  const [newEntityDesc, setNewEntityDesc] = useState('');
  const [newEntityTier, setNewEntityTier] = useState<ClassificationLevel>('INTERNAL');
  const [newEntityOwner, setNewEntityOwner] = useState('TEAM-RELIABILITY');

  // Form states: Create Relationship
  const [relSourceId, setRelSourceId] = useState('');
  const [relType, setRelType] = useState<RelationType>('DEPENDS_ON');
  const [relTargetId, setRelTargetId] = useState('');
  const [relDesc, setRelDesc] = useState('');
  const [relEvidenceIds, setRelEvidenceIds] = useState('');

  const isViewer = currentRole === 'viewer';

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      if (activeTab === 'entities') {
        const res = await semantiqApi.listManagedEntities(entityStatusFilter || undefined, entityTypeFilter || undefined);
        setEntities(res.entities || []);
      } else if (activeTab === 'relationships') {
        const res = await semantiqApi.listManagedRelationships();
        setRelationships(res.relationships || []);
      } else if (activeTab === 'pending') {
        const res = await semantiqApi.listPendingRelationships();
        setPendingRelationships(res.relationships || []);
      } else if (activeTab === 'changes') {
        const res = await semantiqApi.getChangeAuditLogs(50);
        setChangeLogs(res.changes || []);
      }
    } catch (err: any) {
      console.error('Failed to load knowledge data:', err);
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to load knowledge records.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEntity = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await semantiqApi.createEntity({
        id: newEntityId.trim().toUpperCase(),
        type: newEntityType,
        name: newEntityName.trim(),
        description: newEntityDesc.trim(),
        access_tier: newEntityTier,
        owner_team: newEntityOwner.trim(),
      });
      setStatusMessage({ type: 'success', text: `Entity ${newEntityId} created successfully.` });
      setShowCreateEntityModal(false);
      resetEntityForm();
      await loadData();
      if (onRefreshGraph) onRefreshGraph();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to create entity.' });
    } finally {
      setLoading(false);
    }
  };

  const handleArchiveEntity = async (entityId: string) => {
    if (!window.confirm(`Are you sure you want to soft-archive entity ${entityId}? Historical audit records will be preserved.`)) {
      return;
    }
    try {
      setLoading(true);
      await semantiqApi.archiveEntity(entityId, 'Archived by authorized operator via Knowledge Management UI.');
      setStatusMessage({ type: 'success', text: `Entity ${entityId} transitioned to ARCHIVED status.` });
      await loadData();
      if (onRefreshGraph) onRefreshGraph();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to archive entity.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRelationship = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const evs = relEvidenceIds ? relEvidenceIds.split(',').map((s) => s.trim()).filter(Boolean) : [];
      const res = await semantiqApi.createRelationship({
        source_entity_id: relSourceId.trim().toUpperCase(),
        relationship_type: relType,
        target_entity_id: relTargetId.trim().toUpperCase(),
        description: relDesc.trim() || undefined,
        evidence_ids: evs,
      });
      const status = res.relationship?.status;
      setStatusMessage({
        type: 'success',
        text: status === 'VERIFIED'
          ? `Authoritative relationship ${res.relationship.id} established.`
          : `Relationship proposed. Placed in PENDING_VERIFICATION queue for human review.`
      });
      setShowCreateRelModal(false);
      resetRelForm();
      await loadData();
      if (onRefreshGraph) onRefreshGraph();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Relationship creation failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteReview = async () => {
    if (!reviewModalRel) return;
    try {
      setLoading(true);
      if (reviewAction === 'verify') {
        await semantiqApi.verifyRelationship(reviewModalRel.id, reviewComment);
        setStatusMessage({ type: 'success', text: `Relationship ${reviewModalRel.id} VERIFIED and activated in GraphRAG engine.` });
      } else {
        await semantiqApi.rejectRelationship(reviewModalRel.id, reviewComment);
        setStatusMessage({ type: 'success', text: `Relationship ${reviewModalRel.id} REJECTED.` });
      }
      setReviewModalRel(null);
      setReviewComment('');
      await loadData();
      if (onRefreshGraph) onRefreshGraph();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Review decision failed.' });
    } finally {
      setLoading(false);
    }
  };

  const resetEntityForm = () => {
    setNewEntityId('');
    setNewEntityName('');
    setNewEntityDesc('');
    setNewEntityType('system');
    setNewEntityTier('INTERNAL');
    setNewEntityOwner('TEAM-RELIABILITY');
  };

  const resetRelForm = () => {
    setRelSourceId('');
    setRelTargetId('');
    setRelDesc('');
    setRelEvidenceIds('');
    setRelType('DEPENDS_ON');
  };

  const filteredEntities = entities.filter((e) => {
    const q = entitySearch.toLowerCase();
    return (
      e.id.toLowerCase().includes(q) ||
      e.name.toLowerCase().includes(q) ||
      e.description.toLowerCase().includes(q)
    );
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-white font-mono">Knowledge Management</h1>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300">
              Source of Truth
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-normal">
            Controlled organizational ontology lifecycle, human verification workflow, and auditable mutations.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {!isViewer && (
            <>
              <button
                onClick={() => { resetEntityForm(); setShowCreateEntityModal(true); }}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium flex items-center space-x-1.5 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Propose Entity</span>
              </button>
              <button
                onClick={() => { resetRelForm(); setShowCreateRelModal(true); }}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono font-medium flex items-center space-x-1.5 transition-colors"
              >
                <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
                <span>Propose Relationship</span>
              </button>
            </>
          )}
          <button
            onClick={loadData}
            title="Refresh records"
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Status notification banner */}
      {statusMessage && (
        <div className={`p-3 rounded-xl border flex items-center space-x-2.5 text-xs font-mono ${
          statusMessage.type === 'success'
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
            : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
        }`}>
          {statusMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-rose-400" />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Sub-Tabs */}
      <div className="flex space-x-1 border-b border-slate-800 bg-slate-900/40 p-1 rounded-xl">
        <button
          onClick={() => setActiveTab('entities')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'entities'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          Entities Catalogue
        </button>
        <button
          onClick={() => setActiveTab('relationships')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-mono font-medium transition-all ${
            activeTab === 'relationships'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          Relationships Matrix
        </button>
        <button
          onClick={() => setActiveTab('pending')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-mono font-medium transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'pending'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Pending Verification</span>
          {pendingRelationships.length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 font-bold text-[10px]">
              {pendingRelationships.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('changes')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-mono font-medium transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'changes'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Change Audit Ledger</span>
        </button>
      </div>

      {/* Tab 1: Entities */}
      {activeTab === 'entities' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={entitySearch}
                onChange={(e) => setEntitySearch(e.target.value)}
                placeholder="Search entities by ID, name, or description..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
            <div className="flex space-x-2 w-full sm:w-auto">
              <select
                value={entityTypeFilter}
                onChange={(e) => { setEntityTypeFilter(e.target.value); }}
                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none"
              >
                <option value="">All Types</option>
                <option value="project">Projects</option>
                <option value="system">Systems</option>
                <option value="incident">Incidents</option>
                <option value="team">Teams</option>
                <option value="document">Documents</option>
                <option value="policy">Policies</option>
              </select>
              <select
                value={entityStatusFilter}
                onChange={(e) => { setEntityStatusFilter(e.target.value); }}
                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono focus:outline-none"
              >
                <option value="ACTIVE">Active</option>
                <option value="ARCHIVED">Archived</option>
                <option value="">All Statuses</option>
              </select>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 font-mono text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Entity ID</th>
                    <th className="py-3 px-4">Name</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Clearance</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Created By / Provenance</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filteredEntities.map((ent) => (
                    <tr key={ent.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">{ent.id}</td>
                      <td className="py-3 px-4 text-slate-200">{ent.name}</td>
                      <td className="py-3 px-4">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30 text-indigo-300 uppercase">
                          {ent.type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`text-[10px] px-2 py-0.5 rounded border ${
                          ent.access_tier === 'RESTRICTED' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
                          ent.access_tier === 'CONFIDENTIAL' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
                          'bg-slate-500/20 text-slate-300 border-slate-500/40'
                        }`}>
                          {ent.access_tier}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`text-[10px] px-2 py-0.5 rounded ${
                          ent.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {ent.status} (v{ent.version})
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        <div>{ent.created_by}</div>
                        <div className="text-[10px] text-slate-500">{new Date(ent.created_at).toLocaleDateString()}</div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {!isViewer && ent.status === 'ACTIVE' && (
                          <button
                            onClick={() => handleArchiveEntity(ent.id)}
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                            title="Soft-archive entity"
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {filteredEntities.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">
                        No entities found matching active clearance and filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Relationships Matrix */}
      {activeTab === 'relationships' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 font-mono text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Source Entity</th>
                    <th className="py-3 px-4">Relationship</th>
                    <th className="py-3 px-4">Target Entity</th>
                    <th className="py-3 px-4">Verification Status</th>
                    <th className="py-3 px-4">Provenance</th>
                    <th className="py-3 px-4">Review Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {relationships.map((rel) => (
                    <tr key={rel.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">{rel.source_entity_id}</td>
                      <td className="py-3 px-4">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300">
                          {rel.relationship_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold text-white">{rel.target_entity_id}</td>
                      <td className="py-3 px-4">
                        <span className={`text-[10px] px-2 py-0.5 rounded border ${
                          rel.status === 'VERIFIED' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                          rel.status === 'PENDING_VERIFICATION' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
                          'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        }`}>
                          {rel.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        <div>{rel.created_by}</div>
                        <div className="text-[10px] text-slate-500">{new Date(rel.created_at).toLocaleDateString()}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {rel.reviewed_by ? (
                          <>
                            <div className="text-emerald-300">{rel.reviewed_by}</div>
                            <div className="text-[10px] text-slate-500">{rel.review_comment || 'Verified'}</div>
                          </>
                        ) : (
                          <span className="text-slate-600">Pending Review</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {relationships.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-500 font-mono text-xs">
                        No relationships recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Pending Verification */}
      {activeTab === 'pending' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs font-mono text-amber-300 flex items-center space-x-2">
            <Clock className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Human Review Inbox: Proposed relationships must be explicitly verified by authorized personnel before being included in active GraphRAG reasoning.
            </span>
          </div>

          <div className="space-y-3">
            {pendingRelationships.map((rel) => (
              <div
                key={rel.id}
                className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-2 font-mono">
                  <div className="flex items-center space-x-2 text-sm">
                    <span className="font-bold text-white">{rel.source_entity_id}</span>
                    <ArrowRight className="w-4 h-4 text-indigo-400" />
                    <span className="px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/40 text-indigo-300 text-xs">
                      {rel.relationship_type}
                    </span>
                    <ArrowRight className="w-4 h-4 text-indigo-400" />
                    <span className="font-bold text-white">{rel.target_entity_id}</span>
                  </div>

                  <p className="text-xs text-slate-400">{rel.description || 'No description provided.'}</p>

                  <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                    <span>Proposed by: <span className="text-slate-300">{rel.created_by}</span></span>
                    <span>•</span>
                    <span>{new Date(rel.created_at).toLocaleString()}</span>
                  </div>
                </div>

                {!isViewer && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => {
                        setReviewModalRel(rel);
                        setReviewAction('verify');
                        setReviewComment('Verified relationship topology and evidence.');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-medium flex items-center space-x-1.5 transition-colors shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => {
                        setReviewModalRel(rel);
                        setReviewAction('reject');
                        setReviewComment('Unsubstantiated or redundant relationship.');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-rose-950 hover:bg-rose-900 border border-rose-500/40 text-rose-300 font-mono text-xs font-medium flex items-center space-x-1.5 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                )}
              </div>
            ))}

            {pendingRelationships.length === 0 && (
              <div className="p-12 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
                ✓ All proposed relationships have been reviewed. Queue is clear.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Change Audit Ledger */}
      {activeTab === 'changes' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 font-mono text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Target</th>
                    <th className="py-3 px-4">Reason / Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {changeLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 text-slate-400">{new Date(log.timestamp).toLocaleString()}</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-white">{log.actor_user_id}</div>
                        <div className="text-[10px] text-slate-500">{log.actor_role}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300">
                          {log.action_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-200">
                        {log.target_type}: {log.target_id}
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-md truncate">
                        {log.reason || 'Standard update'}
                      </td>
                    </tr>
                  ))}
                  {changeLogs.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500 font-mono text-xs">
                        No change ledger events recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create Entity */}
      {showCreateEntityModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-mono">Propose Knowledge Entity</h3>
              <button onClick={() => setShowCreateEntityModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateEntity} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Entity ID (e.g. SYS-FURN-06, INC-202)</label>
                <input
                  type="text"
                  value={newEntityId}
                  onChange={(e) => setNewEntityId(e.target.value)}
                  placeholder="SYS-PUMP-02"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Entity Type</label>
                <select
                  value={newEntityType}
                  onChange={(e) => setNewEntityType(e.target.value as EntityType)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
                >
                  <option value="system">SYSTEM (Operational Equipment)</option>
                  <option value="project">PROJECT (Engineering Workstream)</option>
                  <option value="incident">INCIDENT (Anomaly / Disruption)</option>
                  <option value="document">DOCUMENT (Technical Spec)</option>
                  <option value="policy">POLICY (Compliance Standard)</option>
                  <option value="team">TEAM (Organizational Group)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Entity Name</label>
                <input
                  type="text"
                  value={newEntityName}
                  onChange={(e) => setNewEntityName(e.target.value)}
                  placeholder="High-Vacuum Sintering Pump 02"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Description &amp; Operational Function</label>
                <textarea
                  value={newEntityDesc}
                  onChange={(e) => setNewEntityDesc(e.target.value)}
                  placeholder="Subsystem purpose and technical boundaries..."
                  rows={2}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">Access Tier</label>
                  <select
                    value={newEntityTier}
                    onChange={(e) => setNewEntityTier(e.target.value as ClassificationLevel)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
                  >
                    <option value="INTERNAL">INTERNAL (Level 2)</option>
                    <option value="CONFIDENTIAL">CONFIDENTIAL (Level 3)</option>
                    {currentRole === 'admin' && (
                      <option value="RESTRICTED">RESTRICTED (Level 4)</option>
                    )}
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Owner Team</label>
                  <input
                    type="text"
                    value={newEntityOwner}
                    onChange={(e) => setNewEntityOwner(e.target.value)}
                    placeholder="TEAM-RELIABILITY"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateEntityModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 font-semibold"
                >
                  Submit Entity
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Relationship */}
      {showCreateRelModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-mono">Propose Graph Connection</h3>
              <button onClick={() => setShowCreateRelModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRelationship} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Source Entity ID</label>
                <input
                  type="text"
                  value={relSourceId}
                  onChange={(e) => setRelSourceId(e.target.value)}
                  placeholder="PRJ-ALPHA"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500 uppercase"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Relationship Type</label>
                <select
                  value={relType}
                  onChange={(e) => setRelType(e.target.value as RelationType)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
                >
                  <option value="DEPENDS_ON">DEPENDS_ON (Operational requirement)</option>
                  <option value="USES">USES (Tooling or utility)</option>
                  <option value="OWNED_BY">OWNED_BY (Accountability)</option>
                  <option value="AFFECTED_BY">AFFECTED_BY (Incident impact)</option>
                  <option value="RELATED_TO">RELATED_TO (General connection)</option>
                  <option value="DOCUMENTED_BY">DOCUMENTED_BY (Specification/SOP)</option>
                  <option value="GOVERNED_BY">GOVERNED_BY (Standard or policy)</option>
                  <option value="MAINTAINED_BY">MAINTAINED_BY (Service team)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Target Entity ID</label>
                <input
                  type="text"
                  value={relTargetId}
                  onChange={(e) => setRelTargetId(e.target.value)}
                  placeholder="SYS-CNC-07"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500 uppercase"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Technical Description</label>
                <input
                  type="text"
                  value={relDesc}
                  onChange={(e) => setRelDesc(e.target.value)}
                  placeholder="Autonomous milling dependence on 5-axis center..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Supporting Evidence IDs (comma-separated)</label>
                <input
                  type="text"
                  value={relEvidenceIds}
                  onChange={(e) => setRelEvidenceIds(e.target.value)}
                  placeholder="EVID-ALPHA-01, DOC-031"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateRelModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 font-semibold"
                >
                  Propose Connection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Review Relationship Decision */}
      {reviewModalRel && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">
                {reviewAction === 'verify' ? 'Approve Relationship' : 'Reject Relationship'}
              </h3>
              <button onClick={() => setReviewModalRel(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
              <div className="font-bold text-white">
                {reviewModalRel.source_entity_id} → [{reviewModalRel.relationship_type}] → {reviewModalRel.target_entity_id}
              </div>
              <div className="text-[11px] text-slate-400">{reviewModalRel.description}</div>
              <div className="text-[10px] text-slate-500">Proposed by: {reviewModalRel.created_by}</div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Reviewer Justification &amp; Audit Comment</label>
              <textarea
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                rows={3}
                placeholder="State basis of verification (e.g. cross-referenced electrical schematic)..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setReviewModalRel(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteReview}
                disabled={loading}
                className={`px-3 py-1.5 rounded-lg text-white font-semibold ${
                  reviewAction === 'verify' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'
                }`}
              >
                Confirm {reviewAction === 'verify' ? 'Approval' : 'Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
