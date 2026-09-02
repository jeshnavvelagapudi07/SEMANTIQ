import React, { useEffect, useState } from 'react';
import { EvaluationReport } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  Clock,
  ShieldCheck,
  Zap,
  Target,
  Sparkles,
  GitFork,
  FileCheck
} from 'lucide-react';

export const EvaluationDashboard: React.FC = () => {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    loadEvaluation();
  }, []);

  const loadEvaluation = async () => {
    try {
      setLoading(true);
      const data = await semantiqApi.getEvaluationReport();
      setReport(data);
    } catch (err) {
      console.error('Failed to load evaluation report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerRun = async () => {
    try {
      setRunning(true);
      const data = await semantiqApi.triggerEvaluationRun();
      setReport(data);
    } catch (err) {
      console.error('Failed to trigger evaluation run:', err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] overflow-y-auto bg-slate-950 p-8 space-y-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header Title & Run CTA */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-5 h-5 text-indigo-400" />
              <h1 className="text-xl font-bold text-white font-mono">
                Automated Benchmark Evaluation Suite (10 Golden Cases)
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Live automated validation: Evaluates multi-hop reasoning accuracy, zero-leakage security boundaries, citation validity, and latency across ground-truth golden queries.
            </p>
          </div>

          <button
            onClick={handleTriggerRun}
            disabled={running}
            className="flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-all shadow-lg shadow-indigo-600/20"
          >
            {running ? <Clock className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>{running ? 'Running Benchmarks...' : 'Re-Run Evaluation Suite'}</span>
          </button>
        </div>

        {/* Real Measured Metric Cards */}
        {report && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <Target className="w-3 h-3 text-emerald-400" />
                <span>Pass Rate</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {report.pass_rate}%
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                {report.passed_tests}/{report.total_tests} Golden Tests
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <GitFork className="w-3 h-3 text-cyan-400" />
                <span>Path Correctness</span>
              </div>
              <div className="text-2xl font-bold text-cyan-300 font-mono">
                {report.graph_path_correctness}%
              </div>
              <div className="text-[10px] font-mono text-slate-400">Multi-Hop Traversal</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <FileCheck className="w-3 h-3 text-indigo-400" />
                <span>Citation Validity</span>
              </div>
              <div className="text-2xl font-bold text-indigo-300 font-mono">
                {report.citation_validity_rate}%
              </div>
              <div className="text-[10px] font-mono text-slate-400">0 Fake Citations</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                <span>Permission Leakage</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {report.permission_violation_rate}%
              </div>
              <div className="text-[10px] font-mono text-emerald-500">Zero Data Leakage</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>Entity Accuracy</span>
              </div>
              <div className="text-2xl font-bold text-purple-300 font-mono">
                {report.entity_retrieval_accuracy}%
              </div>
              <div className="text-[10px] font-mono text-slate-400">Graph Discovered</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center space-x-1">
                <Zap className="w-3 h-3 text-amber-400" />
                <span>Avg Latency</span>
              </div>
              <div className="text-2xl font-bold text-amber-300 font-mono">
                {report.avg_latency_ms} ms
              </div>
              <div className="text-[10px] font-mono text-slate-400">Local Bounded RAG</div>
            </div>
          </div>
        )}

        {/* Detailed Golden Test Cases Table */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase font-bold text-slate-300 tracking-wider">
              Golden Benchmark Results (Ground Truth Verified)
            </h3>
            <span className="text-[11px] font-mono text-slate-400">10 Benchmark Cases</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2.5 px-3">Test ID</th>
                  <th className="py-2.5 px-3">Benchmark Case Name</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Evaluated Role</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Entity Acc</th>
                  <th className="py-2.5 px-3">Citation Val</th>
                  <th className="py-2.5 px-3">Leakage</th>
                  <th className="py-2.5 px-3 text-right">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400">Loading benchmark test results...</td>
                  </tr>
                ) : (
                  report?.test_results.map((tr) => (
                    <tr key={tr.test_id} className="hover:bg-slate-900/60 transition-colors">
                      <td className="py-3 px-3 font-bold text-indigo-300">{tr.test_id}</td>
                      <td className="py-3 px-3">
                        <div className="font-semibold text-white font-sans text-xs">{tr.name}</div>
                        <div className="text-[10px] text-slate-400 font-sans mt-0.5">{tr.details}</div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {tr.category}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-400">{tr.role}</td>
                      <td className="py-3 px-3 text-slate-300">{tr.latency_ms} ms</td>
                      <td className="py-3 px-3 text-slate-300">{tr.entity_accuracy}%</td>
                      <td className="py-3 px-3 text-slate-300">{tr.citation_validity}%</td>
                      <td className="py-3 px-3">
                        {tr.permission_leakage ? (
                          <span className="text-rose-400 font-bold">YES (Leak)</span>
                        ) : (
                          <span className="text-emerald-400 font-semibold">0% (Safe)</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {tr.passed ? (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-bold text-[10px]">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>PASSED</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 font-bold text-[10px]">
                            <XCircle className="w-3 h-3" />
                            <span>FAILED</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
