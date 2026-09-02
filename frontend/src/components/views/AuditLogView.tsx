import React, { useEffect, useState } from 'react';
import { UserRole, AuditLogEntry } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  History,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  X,
  FileText,
  Clock,
  Shield,
  Layers,
  Sparkles,
  ArrowRight
} from 'lucide-react';

interface AuditLogViewProps {
  currentRole: UserRole;
  onNavigateToReasoning: (query: string) => void;
}

export const AuditLogView: React.FC<AuditLogViewProps> = ({ currentRole, onNavigateToReasoning }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [selectedLog, setSelectedLog] = useState<any | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAuditLogs();
  }, [currentRole]);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const res = await semantiqApi.getAuditLogs(50);
      setLogs(res.logs);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const openLogDetail = async (logId: string) => {
    try {
      const res = await semantiqApi.getAuditLogDetail(logId);
      setSelectedLog(res);
    } catch (err) {
      console.error('Failed to load log detail:', err);
    }
  };

  const filteredLogs = logs.filter(
    (l) =>
      !search ||
      l.query.toLowerCase().includes(search.toLowerCase()) ||
      l.id.toLowerCase().includes(search.toLowerCase()) ||
      l.user_role.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-[calc(100vh-110px)] flex flex-col bg-slate-950 p-8 overflow-y-auto space-y-6">
      <div className="max-w-7xl mx-auto w-full space-y-6">
        {/* Header Strip */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <History className="w-5 h-5 text-indigo-400" />
              <h1 className="text-xl font-bold text-white font-mono">Auditable Query Ledger</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Complete auditability: Logs every query, user role, retrieved graph paths, authorized vs withheld items, validation status, and human operator approvals.
            </p>
          </div>

          <div className="relative w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search audit ledger..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[11px]">
                  <th className="py-3 px-3">Timestamp / Query ID</th>
                  <th className="py-3 px-3">User Role</th>
                  <th className="py-3 px-3">Query</th>
                  <th className="py-3 px-3">Entities & Paths</th>
                  <th className="py-3 px-3">Pre-LLM Filtered</th>
                  <th className="py-3 px-3">Provider</th>
                  <th className="py-3 px-3">Confidence</th>
                  <th className="py-3 px-3">Approval</th>
                  <th className="py-3 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400">Loading audit trail...</td>
                  </tr>
                ) : filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400">No query audit logs found.</td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => {
                    return (
                      <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3 px-3">
                          <div className="text-white font-bold">{log.id}</div>
                          <div className="text-[10px] text-slate-400">{log.timestamp.slice(0, 19).replace('T', ' ')}</div>
                        </td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-semibold">
                            {log.user_role}
                          </span>
                        </td>
                        <td className="py-3 px-3 max-w-xs truncate text-slate-200 font-sans">
                          {log.query}
                        </td>
                        <td className="py-3 px-3">
                          <div className="text-indigo-300">{log.identified_entities.length} Nodes</div>
                          <div className="text-[10px] text-slate-400">{log.graph_paths_count} Paths</div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] ${
                            log.filtered_entities_count > 0 ? 'bg-amber-950 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {log.filtered_entities_count} Filtered
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-400 truncate max-w-[120px]">
                          {log.llm_provider.split('(')[0]}
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            log.confidence_score >= 75 ? 'text-emerald-400' :
                            log.confidence_score >= 45 ? 'text-amber-400' : 'text-rose-400'
                          }`}>
                            {log.confidence_score}%
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          {log.action_status ? (
                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                              log.action_status === 'APPROVED' ? 'bg-emerald-950 text-emerald-300' :
                              log.action_status === 'REJECTED' ? 'bg-rose-950 text-rose-300' :
                              'bg-amber-950 text-amber-300'
                            }`}>
                              {log.action_status}
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[10px]">N/A</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => openLogDetail(log.id)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] transition-colors"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal Inspector Drawer */}
        {selectedLog && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div>
                  <div className="text-xs font-mono text-indigo-400">Audit Record: {selectedLog.id}</div>
                  <h3 className="text-base font-bold text-white mt-1 font-sans">{selectedLog.query}</h3>
                  <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                    User: {selectedLog.user_id} ({selectedLog.user_role}) • {selectedLog.timestamp}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Identified vs Filtered Details */}
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400 uppercase text-[10px]">Authorized Entities Context:</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedLog.authorized_entities.map((e: string) => (
                      <span key={e} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-white">
                        {e}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400 uppercase text-[10px]">Filtered Pre-LLM Items:</div>
                  <div className="text-amber-400 font-bold">{selectedLog.filtered_entities_count} Items Filtered</div>
                </div>
              </div>

              {/* Evidence Chunks Cited */}
              {selectedLog.evidence_ids && selectedLog.evidence_ids.length > 0 && (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs font-mono">
                  <div className="text-slate-400 uppercase text-[10px]">Evidence Citations Used:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedLog.evidence_ids.map((evId: string) => (
                      <span key={evId} className="px-2 py-1 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300">
                        {evId}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendation & Action Status */}
              {selectedLog.recommendation && (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1 text-xs">
                  <div className="font-mono text-slate-400 uppercase text-[10px]">Operational Recommendation:</div>
                  <p className="text-slate-200 leading-relaxed font-sans">{selectedLog.recommendation}</p>
                  {selectedLog.action_id && (
                    <div className="mt-2 text-xs font-mono text-slate-400">
                      Action ID: <strong className="text-indigo-300">{selectedLog.action_id}</strong> • Status: <strong className="text-emerald-400">{selectedLog.action_status}</strong>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  onClick={() => {
                    setSelectedLog(null);
                    onNavigateToReasoning(selectedLog.query);
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all"
                >
                  Re-Run Query in Workspace
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
