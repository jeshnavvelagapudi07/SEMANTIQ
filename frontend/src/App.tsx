import React, { useState, useEffect } from 'react';
import { UserRole, SystemHealth, AuthUser, AIStatus } from './types';
import { semantiqApi } from './services/api';
import { Header } from './components/layout/Header';
import { Navigation, ActiveTab } from './components/layout/Navigation';
import { LoginScreen } from './components/views/LoginScreen';
import { OverviewKnowledgeMap } from './components/views/OverviewKnowledgeMap';
import { EntityExplorer } from './components/views/EntityExplorer';
import { AIReasoningWorkspace } from './components/views/AIReasoningWorkspace';
import { EvidencePanel } from './components/views/EvidencePanel';
import { ReasoningPathVisualizer } from './components/views/ReasoningPathVisualizer';
import { SecurityAccessView } from './components/views/SecurityAccessView';
import { AuditLogView } from './components/views/AuditLogView';
import { EvaluationDashboard } from './components/views/EvaluationDashboard';
import { KnowledgeManagementView } from './components/views/KnowledgeManagementView';
import { UserManagementView } from './components/views/UserManagementView';

export function App() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [checkingAuth, setCheckingAuth] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [pendingActionsCount, setPendingActionsCount] = useState<number>(0);
  const [pendingKnowledgeCount, setPendingKnowledgeCount] = useState<number>(0);

  // Navigation Preset Parameters
  const [reasoningInitialQuery, setReasoningInitialQuery] = useState<string | undefined>(undefined);
  const [visualizerSourceId, setVisualizerSourceId] = useState<string>('PRJ-GAMMA');
  const [visualizerTargetId, setVisualizerTargetId] = useState<string>('INC-104');

  useEffect(() => {
    initAuthSession();
    loadHealthAndActions();
    // Poll health every 15s, AI status (which involves a real probe) every 60s
    const healthInterval = setInterval(loadHealthAndActions, 15000);
    const aiInterval = setInterval(loadAIStatus, 60000);
    return () => {
      clearInterval(healthInterval);
      clearInterval(aiInterval);
    };
  }, []);

  const initAuthSession = async () => {
    try {
      const storedToken = sessionStorage.getItem('semantiq_token');
      if (storedToken) {
        const me = await semantiqApi.getMe();
        setCurrentUser(me);
      }
    } catch (err) {
      console.warn('Existing session invalid or expired:', err);
      sessionStorage.removeItem('semantiq_token');
      sessionStorage.removeItem('semantiq_user');
      setCurrentUser(null);
    } finally {
      setCheckingAuth(false);
    }
  };

  const loadHealthAndActions = async () => {
    try {
      const [h, acts, pendingK] = await Promise.all([
        semantiqApi.getHealth(),
        semantiqApi.listActions(),
        semantiqApi.listPendingRelationships().catch(() => ({ count: 0, relationships: [] })),
      ]);
      setHealth(h);
      const pending = acts.actions.filter((a) => a.status === 'PENDING').length;
      setPendingActionsCount(pending);
      setPendingKnowledgeCount(pendingK.count || 0);
    } catch (err) {
      console.error('Failed to load health status:', err);
    }
  };

  const loadAIStatus = async () => {
    try {
      const status = await semantiqApi.getAIStatus();
      setAiStatus(status);
    } catch (err) {
      console.warn('Failed to fetch AI status:', err);
    }
  };

  const handleSignOut = async () => {
    await semantiqApi.logout();
    setCurrentUser(null);
    setActiveTab('overview');
  };

  const handleNavigateToReasoning = (presetQuery: string) => {
    setReasoningInitialQuery(presetQuery);
    setActiveTab('reasoning');
  };

  const handleNavigateToPathVisualizer = (sourceId: string, targetId: string) => {
    setVisualizerSourceId(sourceId);
    setVisualizerTargetId(targetId);
    setActiveTab('visualizer');
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        <div className="text-xs font-mono text-slate-400">Verifying security session...</div>
      </div>
    );
  }

  // If unauthenticated, show the Enterprise Persona Login Portal
  if (!currentUser) {
    return <LoginScreen onLoginSuccess={(user) => { setCurrentUser(user); loadAIStatus(); }} />;
  }

  const currentRole = currentUser.role;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <Header
        currentUser={currentUser}
        onSignOut={handleSignOut}
        health={health}
        aiStatus={aiStatus}
      />

      {/* Navigation Bar */}
      <Navigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        currentUserRole={currentRole}
        pendingActionsCount={pendingActionsCount}
        pendingKnowledgeCount={pendingKnowledgeCount}
      />

      {/* Main Viewport */}
      <main className="flex-1">
        {activeTab === 'overview' && (
          <OverviewKnowledgeMap
            currentRole={currentRole}
            onNavigateToReasoning={handleNavigateToReasoning}
          />
        )}

        {activeTab === 'entities' && (
          <EntityExplorer
            currentRole={currentRole}
            onNavigateToReasoning={handleNavigateToReasoning}
            onNavigateToPathVisualizer={handleNavigateToPathVisualizer}
          />
        )}

        {activeTab === 'reasoning' && (
          <AIReasoningWorkspace
            currentRole={currentRole}
            initialQuery={reasoningInitialQuery}
          />
        )}

        {activeTab === 'evidence' && (
          <EvidencePanel
            currentRole={currentRole}
            onNavigateToReasoning={handleNavigateToReasoning}
          />
        )}

        {activeTab === 'visualizer' && (
          <ReasoningPathVisualizer
            currentRole={currentRole}
            initialSourceId={visualizerSourceId}
            initialTargetId={visualizerTargetId}
          />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeManagementView
            currentRole={currentRole}
            onRefreshGraph={loadHealthAndActions}
          />
        )}

        {activeTab === 'security' && (
          <SecurityAccessView
            currentRole={currentRole}
          />
        )}

        {activeTab === 'audit' && (
          <AuditLogView
            currentRole={currentRole}
            onNavigateToReasoning={handleNavigateToReasoning}
          />
        )}

        {activeTab === 'evaluation' && (
          <EvaluationDashboard />
        )}

        {activeTab === 'users' && (
          <UserManagementView />
        )}
      </main>
    </div>
  );
}

export default App;
