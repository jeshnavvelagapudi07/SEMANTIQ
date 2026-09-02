import React from 'react';
import { UserRole, SystemHealth, AuthUser, AIStatus } from '../../types';
import { Shield, Sparkles, Activity, Lock, LogOut, User, AlertCircle, WifiOff } from 'lucide-react';

interface HeaderProps {
  currentUser: AuthUser;
  onSignOut: () => void;
  health: SystemHealth | null;
  aiStatus?: AIStatus | null;
}

const ROLE_LABELS: Record<UserRole, { label: string; clearance: string; badgeColor: string }> = {
  admin: {
    label: 'Administrator',
    clearance: 'RESTRICTED (Level 4 - Full Clearance)',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30'
  },
  operations_engineer: {
    label: 'Operations Engineer',
    clearance: 'CONFIDENTIAL (Level 3 - Operational & Systems)',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  },
  project_manager: {
    label: 'Project Manager',
    clearance: 'CONFIDENTIAL (Level 3 - Projects & Delivery)',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
  },
  viewer: {
    label: 'Viewer / Auditor',
    clearance: 'INTERNAL (Level 2 - General Read-Only)',
    badgeColor: 'bg-slate-500/20 text-slate-300 border-slate-500/30'
  },
};

// Derive a display label and color from the real AI status probe result
function resolveAIBadge(aiStatus: AIStatus | null | undefined, health: SystemHealth | null): {
  label: string;
  colorClass: string;
  icon: 'live' | 'warn' | 'error' | 'none';
} {
  // If we have a real probe result from /api/system/ai-status, use it
  if (aiStatus) {
    if (!aiStatus.configured) {
      return { label: 'No API Key', colorClass: 'bg-slate-950/40 border-slate-500/40 text-slate-300', icon: 'none' };
    }
    if (aiStatus.available && aiStatus.status === 'live') {
      return { label: `Gemini Live (${aiStatus.model})`, colorClass: 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300', icon: 'live' };
    }
    // Categorized error states
    const statusMap: Record<string, { label: string; colorClass: string; icon: 'warn' | 'error' }> = {
      quota_error:        { label: 'Gemini Quota Error',          colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300',   icon: 'warn' },
      authentication_error: { label: 'Gemini Auth Error',         colorClass: 'bg-rose-950/40 border-rose-500/40 text-rose-300',     icon: 'error' },
      model_error:        { label: 'Gemini Model Error',          colorClass: 'bg-rose-950/40 border-rose-500/40 text-rose-300',     icon: 'error' },
      service_unavailable:{ label: 'Gemini Unavailable',          colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300',  icon: 'warn' },
      timeout:            { label: 'Gemini Timeout',              colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300',  icon: 'warn' },
      network_error:      { label: 'Gemini Network Error',        colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300',  icon: 'warn' },
      api_error:          { label: 'Gemini API Error',            colorClass: 'bg-rose-950/40 border-rose-500/40 text-rose-300',     icon: 'error' },
      invalid_response:   { label: 'Gemini Response Error',       colorClass: 'bg-rose-950/40 border-rose-500/40 text-rose-300',     icon: 'error' },
      unconfigured:       { label: 'Gemini Not Configured',       colorClass: 'bg-slate-950/40 border-slate-500/40 text-slate-300',  icon: 'none' as any },
    };
    const mapped = statusMap[aiStatus.status];
    if (mapped) return mapped;
    return { label: `Gemini ${aiStatus.status}`, colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300', icon: 'warn' };
  }

  // Fallback to health endpoint data while ai-status is loading
  if (!health) {
    return { label: 'Connecting...', colorClass: 'bg-slate-950/40 border-slate-500/40 text-slate-400', icon: 'none' };
  }
  if (health.is_gemini_configured) {
    return { label: health.ai_provider || 'Gemini (checking...)', colorClass: 'bg-slate-950/40 border-slate-500/40 text-slate-300', icon: 'none' };
  }
  return { label: 'Deterministic Fallback', colorClass: 'bg-amber-950/40 border-amber-500/40 text-amber-300', icon: 'warn' };
}

export const Header: React.FC<HeaderProps> = ({ currentUser, onSignOut, health, aiStatus }) => {
  const currentRoleInfo = ROLE_LABELS[currentUser.role] || ROLE_LABELS.operations_engineer;
  const aiBadge = resolveAIBadge(aiStatus, health);

  return (
    <header className="border-b border-slate-800 bg-slate-925/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div className="flex items-center justify-between">
        {/* Brand & Identity */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-slate-900 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-500/10">
              <span className="text-white font-mono font-bold text-lg tracking-tight">Q</span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-wide font-mono">SEMANTIQ</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300">
                  セマンティック
                </span>
                <span className="text-xs text-slate-400 font-mono hidden sm:inline">v1.0.0</span>
              </div>
              <p className="text-xs text-slate-400 font-normal">
                Permission-Aware Organizational Knowledge Graph &amp; GraphRAG
              </p>
            </div>
          </div>
        </div>

        {/* Center/Right Status & Controls */}
        <div className="flex items-center space-x-4">
          {/* AI Provider Badge — driven by real /api/system/ai-status probe */}
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-mono ${aiBadge.colorClass}`}>
            {aiBadge.icon === 'live' && (
              <Sparkles className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            )}
            {aiBadge.icon === 'warn' && (
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            )}
            {aiBadge.icon === 'error' && (
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
            )}
            {aiBadge.icon === 'none' && (
              <Sparkles className="w-3.5 h-3.5 text-slate-400" />
            )}
            <span className="text-slate-400">AI Engine:</span>
            <span className="font-semibold">{aiBadge.label}</span>
          </div>

          {/* System Health */}
          <div className="hidden lg:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-xs text-slate-300 font-mono">
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
            <span>KG Nodes: {health?.knowledge_graph?.nodes || 45}</span>
            <span className="text-slate-600">•</span>
            <span>Edges: {health?.knowledge_graph?.edges || 88}</span>
          </div>

          {/* Server-Enforced Authenticated User Identity — NO role switching */}
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-xl p-1.5 pl-3">
            <div className="flex items-center space-x-2 text-xs">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              <div className="hidden sm:block">
                <div className="font-bold text-white leading-none">{currentUser.display_name}</div>
                <div className="text-[10px] text-slate-400 font-mono mt-0.5">{currentRoleInfo.label}</div>
              </div>
            </div>

            <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${currentRoleInfo.badgeColor}`}>
              {currentUser.role}
            </span>

            {/* Sign Out only — role switching is not permitted */}
            <button
              onClick={onSignOut}
              title="Sign out of SEMANTIQ"
              className="p-1.5 text-slate-400 hover:text-rose-300 hover:bg-rose-950/40 rounded-lg border border-transparent hover:border-rose-500/30 transition-all text-xs flex items-center space-x-1"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="text-[11px] font-mono hidden md:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
