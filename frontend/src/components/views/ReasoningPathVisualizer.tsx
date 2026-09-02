import React, { useState, useEffect } from 'react';
import { UserRole, GraphPath } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  GitFork,
  ArrowRight,
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Clock,
  Layers
} from 'lucide-react';

interface ReasoningPathVisualizerProps {
  currentRole: UserRole;
  initialSourceId?: string;
  initialTargetId?: string;
}

const PRESET_PAIRS = [
  { source: 'PRJ-GAMMA', target: 'INC-104', label: 'Project C ➔ Incident 104 (Risk Chain Demo)' },
  { source: 'PRJ-ALPHA', target: 'SYS-COOL-02', label: 'Project Alpha ➔ Coolant Chiller 02' },
  { source: 'INC-104', target: 'POL-SAFE-01', label: 'Incident 104 ➔ Machinery Safety Policy' },
  { source: 'PRJ-DELTA', target: 'SYS-FURN-05', label: 'Project Delta ➔ Induction Furnace 05' },
  { source: 'PRJ-EPSILON', target: 'SYS-AIR-04', label: 'Project Epsilon ➔ Cleanroom HEPA Unit' },
];

export const ReasoningPathVisualizer: React.FC<ReasoningPathVisualizerProps> = ({
  currentRole,
  initialSourceId = 'PRJ-GAMMA',
  initialTargetId = 'INC-104',
}) => {
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [targetId, setTargetId] = useState(initialTargetId);
  const [paths, setPaths] = useState<GraphPath[]>([]);
  const [explanation, setExplanation] = useState<string>('');
  const [supportingEvidence, setSupportingEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    handleTracePath(sourceId, targetId);
  }, [currentRole]);

  const handleTracePath = async (src: string, tgt: string) => {
    if (!src || !tgt) return;
    try {
      setLoading(true);
      const res = await semantiqApi.explainPath(src, tgt, currentRole);
      setPaths(res.paths || []);
      setExplanation(res.explanation || '');
      setSupportingEvidence(res.supporting_evidence || []);
    } catch (err) {
      console.error('Failed to trace path:', err);
      setPaths([]);
      setExplanation('Failed to trace authorized path between selected nodes.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] flex flex-col bg-slate-950 overflow-hidden">
      {/* Top Selector Bar */}
      <div className="p-5 border-b border-slate-800 bg-slate-925/90 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <GitFork className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-mono uppercase font-bold text-slate-300 tracking-wider">
              Multi-Hop Reasoning Path Visualizer
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">Role: {currentRole}</span>
        </div>

        {/* Source & Target Inputs */}
        <div className="flex items-center space-x-3">
          <div className="flex-1">
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Source Entity ID</label>
            <input
              type="text"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value.toUpperCase())}
              placeholder="e.g. PRJ-GAMMA"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-4 text-slate-500 font-bold">➔</div>

          <div className="flex-1">
            <label className="block text-[10px] font-mono uppercase text-slate-400 mb-1">Target Entity ID</label>
            <input
              type="text"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value.toUpperCase())}
              placeholder="e.g. INC-104"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-4">
            <button
              onClick={() => handleTracePath(sourceId, targetId)}
              disabled={loading}
              className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
            >
              {loading ? <Clock className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              <span>Trace & Explain Path</span>
            </button>
          </div>
        </div>

        {/* Preset Quick Pairs */}
        <div className="flex items-center space-x-2 overflow-x-auto pt-1">
          <span className="text-[10px] font-mono uppercase text-slate-400 whitespace-nowrap">Presets:</span>
          {PRESET_PAIRS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSourceId(p.source);
                setTargetId(p.target);
                handleTracePath(p.source, p.target);
              }}
              className="px-2.5 py-1 rounded bg-slate-900 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-500/40 text-xs text-slate-300 font-mono transition-all whitespace-nowrap"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Visual Canvas & Explanation */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center space-y-3">
            <Clock className="w-8 h-8 text-indigo-400 animate-spin" />
            <span className="text-xs font-mono text-slate-400">Traversing Knowledge Graph paths...</span>
          </div>
        ) : paths.length > 0 ? (
          <div className="max-w-5xl mx-auto space-y-6">
            {/* Step-by-Step Interactive Chain */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-xs font-mono uppercase font-bold text-slate-300 tracking-wider flex items-center space-x-1.5">
                  <GitFork className="w-4 h-4 text-indigo-400" />
                  <span>Traversed Graph Path ({paths[0].length} Hops)</span>
                </h3>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                  Verified Causal Chain
                </span>
              </div>

              {/* Graphical Chain Flow */}
              <div className="flex flex-wrap items-center gap-3 py-6 justify-center bg-slate-950/80 p-6 rounded-xl border border-slate-800">
                {paths[0].path_nodes.map((nodeId, idx) => (
                  <React.Fragment key={nodeId}>
                    {/* Node Box */}
                    <div className="p-4 rounded-xl bg-slate-900 border border-indigo-500/40 shadow-lg min-w-[150px] text-center space-y-1">
                      <div className="text-[10px] font-mono uppercase text-indigo-400 font-semibold">
                        Step {idx + 1}
                      </div>
                      <div className="font-bold text-sm text-white font-mono">{nodeId}</div>
                    </div>

                    {/* Edge Arrow */}
                    {idx < paths[0].path_nodes.length - 1 && (
                      <div className="flex flex-col items-center px-2">
                        <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                          {paths[0].path_relationships[idx]}
                        </span>
                        <div className="text-indigo-400 font-bold text-lg">➔</div>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* AI Grounded Path Explanation */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
              <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <h3 className="text-xs font-mono uppercase font-bold text-indigo-300">
                  Grounded Connection Explanation
                </h3>
              </div>
              <p className="text-sm text-slate-200 leading-relaxed font-sans">{explanation}</p>
            </div>

            {/* Supporting Evidence Chunks */}
            {supportingEvidence.length > 0 && (
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
                <h3 className="text-xs font-mono uppercase font-bold text-slate-400 tracking-wider">
                  Supporting Authorized Evidence ({supportingEvidence.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {supportingEvidence.map((ev, i) => (
                    <div key={i} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                      <div className="flex justify-between items-center text-xs font-mono">
                        <span className="font-bold text-indigo-300">{ev.id} ({ev.doc_id})</span>
                        <span className="text-slate-400">{ev.source_type}</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">{ev.excerpt}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400 text-xs font-mono">
            No authorized graph path found between '{sourceId}' and '{targetId}'.
          </div>
        )}
      </div>
    </div>
  );
};
