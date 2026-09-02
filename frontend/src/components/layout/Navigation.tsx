import React from 'react';
import {
  Network,
  Search,
  BrainCircuit,
  FileText,
  GitFork,
  ShieldAlert,
  History,
  BarChart3,
  Layers,
  Users,
} from 'lucide-react';
import { UserRole } from '../../types';

export type ActiveTab =
  | 'overview'
  | 'entities'
  | 'reasoning'
  | 'evidence'
  | 'visualizer'
  | 'knowledge'
  | 'security'
  | 'audit'
  | 'evaluation'
  | 'users';

interface NavigationProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  currentUserRole?: UserRole;
  pendingActionsCount?: number;
  pendingKnowledgeCount?: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  currentUserRole,
  pendingActionsCount = 0,
  pendingKnowledgeCount = 0
}) => {
  const tabs: { id: ActiveTab; label: string; icon: React.FC<{ className?: string }>; adminOnly?: boolean }[] = [
    { id: 'overview', label: 'Knowledge Map', icon: Network },
    { id: 'entities', label: 'Entity Explorer', icon: Search },
    { id: 'reasoning', label: 'AI Reasoning', icon: BrainCircuit },
    { id: 'evidence', label: 'Evidence Panel', icon: FileText },
    { id: 'visualizer', label: 'Path Visualizer', icon: GitFork },
    { id: 'knowledge', label: 'Knowledge Management', icon: Layers },
    { id: 'security', label: 'Security & Access', icon: ShieldAlert },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'evaluation', label: 'Evaluation & Benchmarks', icon: BarChart3 },
    { id: 'users', label: 'User Management', icon: Users, adminOnly: true },
  ];

  const visibleTabs = tabs.filter((t) => !t.adminOnly || currentUserRole === 'admin');

  return (
    <nav className="border-b border-slate-800 bg-slate-900/60 px-6">
      <div className="flex items-center space-x-1 overflow-x-auto py-2">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
              {tab.id === 'reasoning' && pendingActionsCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] flex items-center justify-center font-mono">
                  {pendingActionsCount}
                </span>
              )}
              {tab.id === 'knowledge' && pendingKnowledgeCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-amber-500 text-slate-950 text-[10px] flex items-center justify-center font-mono font-bold">
                  {pendingKnowledgeCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
