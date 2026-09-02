import React, { useState, useEffect } from 'react';
import { UserRole, QueryResponse, ActionItem } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  BrainCircuit,
  Sparkles,
  Send,
  ShieldCheck,
  ShieldAlert,
  GitFork,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Layers,
  Network
} from 'lucide-react';

interface AIReasoningWorkspaceProps {
  currentRole: UserRole;
  initialQuery?: string;
}

const PRESET_DEMO_QUERIES = [
  {
    label: 'Incident 104 Impact & SOP (Killer Demo 1)',
    query: 'Which projects are affected by Incident 104 and what should the responsible team do?',
  },
  {
    label: 'Project C Risk Chain (Killer Demo 2)',
    query: 'Why is Project C considered high risk?',
  },
  {
    label: 'CNC-07 & Dependent Projects (Intent Demo)',
    query: 'What is CNC-07 and what projects depend on it?',
  },
  {
    label: 'Project Delta Dependencies (Zero Contamination)',
    query: 'What is Project Delta and which system does it depend on?',
  },
  {
    label: 'Delta Evidence Grounding (Tri-Concept Demo)',
    query: 'What evidence proves that Project Delta depends on SYS-FURN-05?',
  },
  {
    label: 'Restricted Contract Terms (Security Demo)',
    query: 'What are the contract terms and pricing penalties for Customer X?',
  },
];

export const AIReasoningWorkspace: React.FC<AIReasoningWorkspaceProps> = ({ currentRole, initialQuery }) => {
  const [queryText, setQueryText] = useState(initialQuery || PRESET_DEMO_QUERIES[0].query);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [actionItem, setActionItem] = useState<ActionItem | null>(null);
  const [actionProcessing, setActionProcessing] = useState(false);

  useEffect(() => {
    if (initialQuery) {
      setQueryText(initialQuery);
      handleExecuteQuery(initialQuery);
    }
  }, [initialQuery]);

  const handleExecuteQuery = async (overrideQuery?: string) => {
    const q = overrideQuery || queryText;
    if (!q.trim()) return;

    try {
      setLoading(true);
      // Clean previous state to guarantee state isolation
      setResponse(null);
      setActionItem(null);

      const res = await semantiqApi.executeQuery(q, currentRole, 3);
      setResponse(res);
      setActionItem(res.action_item || null);
    } catch (err) {
      console.error('Query execution failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAction = async () => {
    if (!actionItem) return;
    try {
      setActionProcessing(true);
      const updated = await semantiqApi.approveAction(actionItem.id, 'Verified machine thermal limits and approved standard tag-out.');
      setActionItem(updated);
    } catch (err) {
      console.error('Failed to approve action:', err);
    } finally {
      setActionProcessing(false);
    }
  };

  const handleRejectAction = async () => {
    if (!actionItem) return;
    try {
      setActionProcessing(true);
      const updated = await semantiqApi.rejectAction(actionItem.id, 'Rejected by operator; awaiting secondary sensor recalibration.');
      setActionItem(updated);
    } catch (err) {
      console.error('Failed to reject action:', err);
    } finally {
      setActionProcessing(false);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] flex flex-col bg-slate-950 overflow-hidden">
      {/* Top Query Input & Killer Demo Preset Chips */}
      <div className="p-5 border-b border-slate-800 bg-slate-925/80 backdrop-blur space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BrainCircuit className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-mono uppercase font-bold text-slate-300 tracking-wider">
              AI Reasoning Terminal (Bounded GraphRAG & Zero Contamination)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Active Role: <span className="text-indigo-300 font-semibold">{currentRole}</span>
          </span>
        </div>

        {/* Query Input Bar */}
        <div className="flex items-center space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Ask an organizational question (e.g. What is CNC-07 and what projects depend on it?)..."
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleExecuteQuery()}
              className="w-full pl-4 pr-12 py-3 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 shadow-inner font-sans"
            />
            <button
              onClick={() => handleExecuteQuery()}
              disabled={loading}
              className="absolute right-2 top-2 p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg transition-all shadow-md shadow-indigo-600/30"
            >
              {loading ? <Clock className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Demo Preset Chips */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 pt-0.5">
          <span className="text-[10px] font-mono uppercase text-slate-400 whitespace-nowrap">Core Scenarios:</span>
          {PRESET_DEMO_QUERIES.map((demo, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQueryText(demo.query);
                handleExecuteQuery(demo.query);
              }}
              className="px-3 py-1 rounded-full bg-slate-900 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-500/40 text-xs text-slate-300 hover:text-indigo-200 transition-all whitespace-nowrap font-medium flex items-center space-x-1.5"
            >
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span>{demo.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Workspace Dual Panes */}
      <div className="flex-1 flex overflow-hidden">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-4">
            <div className="w-12 h-12 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            <div className="text-center space-y-1">
              <div className="text-sm font-medium text-white font-mono">Executing Scoped GraphRAG Pipeline...</div>
              <div className="text-xs text-slate-400">
                Intent Classification → Permission Gate → Graph Traversal → Scoped Evidence → Minimized Reasoning
              </div>
            </div>
          </div>
        ) : response ? (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Main Output Pane */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6 border-r border-slate-800 bg-slate-950">
              {/* Answer Card */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-mono uppercase font-bold text-indigo-300">
                      Grounded Synthesis Response
                    </span>
                    {response.query_intent && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300 uppercase">
                        Intent: {response.query_intent}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded border flex items-center space-x-1 font-semibold ${
                      response.provider_used.includes('Gemini Live')
                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/20'
                        : response.provider_used.includes('System Guard')
                        ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/40'
                        : response.provider_used.includes('Gemini Auth') || response.provider_used.includes('Gemini Model')
                        ? 'bg-rose-950/80 text-rose-300 border-rose-500/40'
                        : response.provider_used.includes('Gemini Quota') || response.provider_used.includes('Gemini Service') || response.provider_used.includes('Gemini Timeout')
                        ? 'bg-amber-950/80 text-amber-300 border-amber-500/40'
                        : response.provider_used.startsWith('Gemini') && !response.provider_used.includes('Deterministic')
                        ? 'bg-rose-950/80 text-rose-300 border-rose-500/40'
                        : 'bg-amber-950/80 text-amber-300 border-amber-500/40'
                    }`}>
                      <Sparkles className="w-3 h-3" />
                      <span>{response.provider_used}</span>
                    </span>
                    <span className={`text-[10px] font-mono font-semibold px-2.5 py-0.5 rounded border ${
                      response.confidence.level === 'HIGH' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                      response.confidence.level === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                      'bg-rose-500/20 text-rose-300 border-rose-500/30'
                    }`}>
                      Confidence: {response.confidence.score}% ({response.confidence.level})
                    </span>
                  </div>
                </div>

                <div className="text-slate-100 text-sm leading-relaxed font-sans font-normal">
                  {response.answer}
                </div>

                {/* SOP Recommendation if justified */}
                {response.recommendation && (
                  <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-1.5">
                    <div className="text-xs font-mono uppercase font-semibold text-indigo-300 flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Recommended Operational Procedure</span>
                    </div>
                    <p className="text-xs text-indigo-100 leading-relaxed">{response.recommendation}</p>
                  </div>
                )}

                {/* Missing Information Banner if Insufficient Evidence */}
                {response.is_insufficient_evidence && (
                  <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 space-y-2">
                    <div className="text-xs font-mono uppercase font-semibold text-amber-300 flex items-center space-x-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <span>Zero-Leakage Permission Gate / Missing Evidence</span>
                    </div>
                    <p className="text-xs text-amber-100 leading-relaxed">
                      {response.filtered_items_count > 0 ? (
                        `${response.filtered_items_count} restricted items were withheld before AI processing due to insufficient role clearance for role '${currentRole}'.`
                      ) : (
                        "No authorized documentary evidence was found in the indexed repository."
                      )}
                    </p>
                    {response.missing_information && (
                      <ul className="list-disc list-inside text-xs text-amber-200/80 font-mono space-y-0.5">
                        {response.missing_information.map((m, i) => <li key={i}>{m}</li>)}
                      </ul>
                    )}
                  </div>
                )}

                {/* Grounded Claims with Verified Citation Chips or Graph Fact Badges */}
                {response.claims.length > 0 && (
                  <div className="pt-3 border-t border-slate-800 space-y-2.5">
                    <div className="text-xs font-mono uppercase font-semibold text-slate-400 tracking-wider">
                      Synthesized Claims & Support Status ({response.claims.length})
                    </div>
                    <div className="space-y-2">
                      {response.claims.map((claim, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-start justify-between space-x-3 text-xs"
                        >
                          <div className="flex items-start space-x-2 flex-1">
                            {claim.is_verified ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            ) : claim.support_status === 'GRAPH_VERIFIED' ? (
                              <Network className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                            ) : (
                              <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                            )}
                            <div className="space-y-0.5">
                              <span className="text-slate-200">{claim.text}</span>
                              {claim.unsupported_reason && (
                                <div className="text-[10px] text-slate-400 font-mono italic">
                                  {claim.unsupported_reason}
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center space-x-1 shrink-0">
                            {claim.evidence_ids && claim.evidence_ids.length > 0 ? (
                              claim.evidence_ids.map((eid) => (
                                <span
                                  key={eid}
                                  className="px-2 py-0.5 rounded font-mono text-[10px] bg-indigo-950/80 border border-indigo-500/40 text-indigo-300 font-semibold"
                                >
                                  {eid}
                                </span>
                              ))
                            ) : claim.support_status === 'GRAPH_VERIFIED' ? (
                              <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 font-semibold">
                                GRAPH FACT
                              </span>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Human-in-the-Loop Approval Action Card */}
              {response.requires_human_review && actionItem && (
                <div className={`p-5 rounded-2xl border shadow-xl backdrop-blur transition-all ${
                  actionItem.status === 'APPROVED' ? 'bg-emerald-950/30 border-emerald-500/40' :
                  actionItem.status === 'REJECTED' ? 'bg-rose-950/30 border-rose-500/40' :
                  'bg-slate-900/90 border-amber-500/40 ring-1 ring-amber-500/20'
                }`}>
                  <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center space-x-2">
                      <ShieldAlert className={`w-5 h-5 ${
                        actionItem.status === 'APPROVED' ? 'text-emerald-400' :
                        actionItem.status === 'REJECTED' ? 'text-rose-400' : 'text-amber-400 animate-pulse'
                      }`} />
                      <div>
                        <h4 className="font-bold text-sm text-white">{actionItem.title}</h4>
                        <div className="text-[10px] font-mono text-slate-400">Action ID: {actionItem.id}</div>
                      </div>
                    </div>
                    <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-full uppercase ${
                      actionItem.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                      actionItem.status === 'REJECTED' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                      'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {actionItem.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 my-3 leading-relaxed">
                    {actionItem.description}
                  </p>

                  {actionItem.status === 'PENDING' ? (
                    <div className="flex items-center space-x-3 pt-2">
                      <button
                        onClick={handleApproveAction}
                        disabled={actionProcessing}
                        className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-emerald-600/20"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>Approve Action & Log Audit Trail</span>
                      </button>
                      <button
                        onClick={handleRejectAction}
                        disabled={actionProcessing}
                        className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-3 bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/50 rounded-lg text-xs font-semibold transition-all"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                        <span>Reject Action</span>
                      </button>
                    </div>
                  ) : (
                    <div className="pt-2 text-xs font-mono text-slate-400 flex items-center space-x-2">
                      <span>Reviewed by: <strong className="text-white">{actionItem.reviewed_by}</strong></span>
                      <span>•</span>
                      <span>Comment: <em className="text-slate-300">{actionItem.resolution_comment}</em></span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Side: Explainable Reasoning Trace Pane */}
            <div className="w-[440px] bg-slate-925 p-5 overflow-y-auto space-y-5 border-l border-slate-800">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <h3 className="font-bold text-xs font-mono uppercase text-white tracking-wider">
                    Reasoning Trace & Trust Boundary
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                  Auditable
                </span>
              </div>

              {/* Stage 1: Identified & Authorized Entities */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center justify-between">
                  <span>1. Identified Entities</span>
                  <span className="text-indigo-300 font-semibold">{response.reasoning_trace.authorized_entities.length} Authorized</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {response.reasoning_trace.authorized_entities.map((eid) => (
                    <span key={eid} className="px-2 py-1 rounded bg-slate-950 border border-slate-700 font-mono text-xs text-white">
                      {eid}
                    </span>
                  ))}
                </div>
              </div>

              {/* Stage 2: Zero-Trust Pre-Filtering Boundary */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center justify-between">
                  <span>2. Pre-LLM Permission Filter</span>
                  <span className={`font-mono text-xs font-bold ${
                    response.filtered_items_count > 0 ? 'text-amber-400' : 'text-emerald-400'
                  }`}>
                    {response.filtered_items_count} Items Filtered
                  </span>
                </div>
                {response.filtered_summary.length > 0 ? (
                  <div className="space-y-1.5">
                    {response.filtered_summary.map((f, i) => (
                      <div key={i} className="p-2 rounded bg-slate-950 border border-amber-500/30 text-[11px] font-mono space-y-0.5">
                        <div className="flex justify-between text-amber-300 font-semibold">
                          <span>{f.entity_name}</span>
                          <span className="text-rose-400">{f.classification}</span>
                        </div>
                        <div className="text-slate-400 text-[10px]">{f.reason}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-400 font-mono">
                    ✓ All requested items are within role clearance. Zero leakage.
                  </div>
                )}
              </div>

              {/* Stage 3: Graph Traversal & Graph Facts */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center justify-between">
                  <span>3. Traversed Graph Facts</span>
                  <span className="text-cyan-300 font-mono font-semibold">{response.graph_paths.length} Paths</span>
                </div>
                <div className="space-y-2">
                  {response.graph_paths.map((path, pIdx) => (
                    <div key={pIdx} className="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1.5">
                      <div className="flex items-center space-x-1 font-mono text-[11px] text-indigo-300 overflow-x-auto">
                        {path.path_nodes.map((node, nIdx) => (
                          <React.Fragment key={nIdx}>
                            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-white shrink-0">
                              {node}
                            </span>
                            {nIdx < path.path_nodes.length - 1 && (
                              <span className="text-slate-500 text-[9px] px-1 font-sans">
                                [{path.path_relationships[nIdx] || '->'}]
                              </span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                      {path.description && <div className="text-[10px] text-slate-400 leading-tight">{path.description}</div>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Stage 4: Scoped Documentary Evidence */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center justify-between">
                  <span>4. Scoped Documentary Evidence</span>
                  <span className="text-indigo-300 font-mono font-semibold">{response.evidence.length} Chunks</span>
                </div>
                {response.evidence.length > 0 ? (
                  <div className="space-y-2">
                    {response.evidence.map((ev) => (
                      <div key={ev.id} className="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1 text-xs">
                        <div className="flex justify-between items-center font-mono">
                          <span className="font-semibold text-indigo-300">{ev.id} ({ev.doc_id})</span>
                          <span className="text-[9px] text-slate-400">Score: {ev.relevance_score}</span>
                        </div>
                        <div className="text-slate-300 text-[11px] line-clamp-2 leading-relaxed">{ev.excerpt}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-400 font-mono italic p-2 bg-slate-950 rounded border border-slate-800">
                    No documentary text chunks indexed for this entity. Synthesis is relying on Knowledge Graph facts.
                  </div>
                )}
              </div>

              {/* Stage 5: Confidence Breakdown */}
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center justify-between">
                  <span>5. Deterministic Confidence Model</span>
                  <span className="font-mono text-xs text-white font-bold">{response.confidence.score}%</span>
                </div>
                <div className="space-y-1 text-[11px] font-mono">
                  {response.confidence.decision_factors.map((df, dIdx) => (
                    <div key={dIdx} className="flex justify-between p-1.5 rounded bg-slate-950 border border-slate-800/80">
                      <span className="text-slate-400">{df.factor}:</span>
                      <span className={df.impact === 'POSITIVE' ? 'text-emerald-400' : df.impact === 'NEGATIVE' ? 'text-rose-400' : 'text-slate-300'}>
                        {df.details}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-3">
            <BrainCircuit className="w-12 h-12 text-slate-600" />
            <h3 className="text-base font-bold text-white">Ask an Organizational Question</h3>
            <p className="text-xs text-slate-400 max-w-md leading-relaxed">
              Select one of the Core Scenario chips above or enter a natural-language query to reason across the organizational graph with strict citation grounding and pre-LLM permission checks.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
