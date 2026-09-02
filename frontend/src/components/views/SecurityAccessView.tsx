import React, { useEffect, useState } from 'react';
import { UserRole, ClassificationLevel } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  FileText,
  Play,
  RotateCcw,
  Sparkles
} from 'lucide-react';

interface SecurityAccessViewProps {
  currentRole: UserRole;
  onRoleChange?: (role: UserRole) => void;
}

const CLASSIFICATION_TIERS: Record<ClassificationLevel, { label: string; desc: string; color: string; bg: string }> = {
  PUBLIC: { label: 'PUBLIC', desc: 'Unrestricted enterprise public directories & rosters', color: 'text-slate-300', bg: 'bg-slate-800' },
  INTERNAL: { label: 'INTERNAL', desc: 'Operational engineering docs, specs & SOPs', color: 'text-emerald-300', bg: 'bg-emerald-950/60' },
  CONFIDENTIAL: { label: 'CONFIDENTIAL', desc: 'SCADA architectures, customer deliverables & IP', color: 'text-amber-300', bg: 'bg-amber-950/60' },
  RESTRICTED: { label: 'RESTRICTED', desc: 'Prime pricing contracts & executive compensation', color: 'text-rose-300', bg: 'bg-rose-950/60' },
};

export const SecurityAccessView: React.FC<SecurityAccessViewProps> = ({ currentRole, onRoleChange }) => {
  const [profile, setProfile] = useState<any | null>(null);
  const [matrix, setMatrix] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  // Simulation Sandbox State
  const [simRole, setSimRole] = useState<UserRole>('viewer');
  const [simTargets, setSimTargets] = useState<string>('CONTRACT-22, PAYROLL-2026, INC-104, SYS-CNC-07');
  const [simResult, setSimResult] = useState<any | null>(null);
  const [simLoading, setSimLoading] = useState(false);

  useEffect(() => {
    loadSecurityData();
  }, [currentRole]);

  const loadSecurityData = async () => {
    try {
      setLoading(true);
      const [p, m] = await Promise.all([
        semantiqApi.getSecurityProfile(currentRole),
        semantiqApi.getSecurityMatrix(),
      ]);
      setProfile(p);
      setMatrix(m);
    } catch (err) {
      console.error('Failed to load security profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunSimulation = async () => {
    try {
      setSimLoading(true);
      const entityIds = simTargets.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await semantiqApi.simulateSecurityCheck(simRole, entityIds);
      setSimResult(res);
    } catch (err) {
      console.error('Simulation failed:', err);
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] overflow-y-auto bg-slate-950 p-8 space-y-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header Title */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <h1 className="text-xl font-bold text-white font-mono">Zero-Trust Pre-LLM Permission Gate</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Guaranteed Least-Privilege Architecture: Unauthorized organizational entities and evidence are pruned BEFORE graph traversal and LLM context construction.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">Current Active Role:</span>
            <span className="font-bold text-indigo-300 uppercase px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30">
              {currentRole}
            </span>
          </div>
        </div>

        {/* Distribution Summary Cards */}
        {profile && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-2">
              <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                <span className="flex items-center space-x-1.5">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Knowledge Graph Entities</span>
                </span>
                <span className="text-emerald-400 font-bold">{profile.accessible_summary.entities.accessible} Accessible</span>
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {profile.accessible_summary.entities.accessible} / {profile.accessible_summary.entities.total}
              </div>
              <div className="text-xs font-mono text-rose-400">
                {profile.accessible_summary.entities.restricted} restricted items filtered for this role
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-2">
              <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                <span className="flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-blue-400" />
                  <span>Documents & SOPs</span>
                </span>
                <span className="text-emerald-400 font-bold">{profile.accessible_summary.documents.accessible} Accessible</span>
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {profile.accessible_summary.documents.accessible} / {profile.accessible_summary.documents.total}
              </div>
              <div className="text-xs font-mono text-rose-400">
                {profile.accessible_summary.documents.restricted} documents filtered (e.g. Contracts & Payroll)
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-2">
              <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                <span className="flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Evidence Chunks</span>
                </span>
                <span className="text-emerald-400 font-bold">{profile.accessible_summary.evidence_chunks.accessible} Accessible</span>
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {profile.accessible_summary.evidence_chunks.accessible} / {profile.accessible_summary.evidence_chunks.total}
              </div>
              <div className="text-xs font-mono text-rose-400">
                {profile.accessible_summary.evidence_chunks.restricted} chunks withheld from LLM
              </div>
            </div>
          </div>
        )}

        {/* Role-to-Classification Matrix Table */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase font-bold text-slate-300 tracking-wider">
              Organizational Role Clearance Matrix
            </h3>
            <span className="text-[11px] font-mono text-slate-400">4 Access Tiers</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">PUBLIC</th>
                  <th className="py-2.5 px-3">INTERNAL</th>
                  <th className="py-2.5 px-3">CONFIDENTIAL</th>
                  <th className="py-2.5 px-3">RESTRICTED</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {matrix &&
                  Object.entries(matrix.matrix).map(([r, allowedTiers]: any) => {
                    const isCurrent = r === currentRole;
                    return (
                      <tr key={r} className={isCurrent ? 'bg-indigo-950/30' : 'hover:bg-slate-900/40'}>
                        <td className="py-3 px-3 font-semibold text-white flex items-center space-x-2">
                          <span>{r}</span>
                          {isCurrent && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500 text-white uppercase">
                              Active
                            </span>
                          )}
                        </td>
                        {['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'].map((tier) => {
                          const isAllowed = allowedTiers.includes(tier);
                          return (
                            <td key={tier} className="py-3 px-3">
                              {isAllowed ? (
                                <span className="inline-flex items-center space-x-1 text-emerald-400">
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  <span>Allowed</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center space-x-1 text-rose-400">
                                  <Lock className="w-3.5 h-3.5" />
                                  <span>Blocked</span>
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Interactive Zero-Leakage Permission Sandbox Simulator */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Play className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-mono uppercase font-bold text-white tracking-wider">
                Pre-LLM Permission Sandbox Simulator
              </h3>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
              Interactive Test Bench
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1.5">Simulate User Role</label>
              <select
                value={simRole}
                onChange={(e) => setSimRole(e.target.value as UserRole)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="viewer">Viewer (Baseline Level 2)</option>
                <option value="operations_engineer">Operations Engineer (Level 3)</option>
                <option value="project_manager">Project Manager (Level 3)</option>
                <option value="admin">Administrator (Level 4 Full Clearance)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1.5">
                Target Entity IDs to Evaluate
              </label>
              <input
                type="text"
                value={simTargets}
                onChange={(e) => setSimTargets(e.target.value)}
                placeholder="e.g. CONTRACT-22, INC-104, SYS-CNC-07"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={simLoading}
            className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Simulate Pre-LLM Filtering</span>
          </button>

          {/* Simulation Output */}
          {simResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Simulation Result for Role: <strong className="text-indigo-300">{simResult.role}</strong></span>
                <span className="text-emerald-400 font-bold">{simResult.authorized_count} Authorized / {simResult.filtered_count} Filtered</span>
              </div>

              {simResult.filtered_details.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-mono uppercase text-rose-400 font-semibold">Filtered Items (Withheld Before LLM):</div>
                  {simResult.filtered_details.map((f: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded bg-slate-900/80 border border-rose-500/30 text-xs font-mono flex items-center justify-between">
                      <div className="space-y-0.5">
                        <span className="font-bold text-white">{f.entity_name} ({f.entity_id})</span>
                        <div className="text-[10px] text-slate-400">{f.reason}</div>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 border border-rose-500/30 text-rose-300 font-bold">
                        {f.classification}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-xs font-mono text-indigo-300 flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>{simResult.zero_leakage_guarantee}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
