import React, { useState } from 'react';
import { AuthUser } from '../../types';
import { semantiqApi } from '../../services/api';
import { Shield, Lock, Mail, ArrowRight, Sparkles, Key, AlertCircle, User, ShieldCheck } from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: AuthUser) => void;
}

const SEED_PERSONAS = [
  {
    email: 'kenji.sato@semantiq.org',
    password: 'Password123!',
    name: 'Kenji Sato',
    title: 'Lead Reliability & Operations Engineer',
    role: 'operations_engineer',
    clearance: 'Level 3 — CONFIDENTIAL',
    clearanceBadge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    avatarLetter: 'KS',
  },
  {
    email: 'elena.rostova@semantiq.org',
    password: 'Password123!',
    name: 'Elena Rostova',
    title: 'Principal Delivery & Project Director',
    role: 'project_manager',
    clearance: 'Level 3 — CONFIDENTIAL',
    clearanceBadge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
    avatarLetter: 'ER',
  },
  {
    email: 'marcus.vance@semantiq.org',
    password: 'Password123!',
    name: 'Marcus Vance',
    title: 'Independent Compliance & Safety Auditor',
    role: 'viewer',
    clearance: 'Level 2 — INTERNAL',
    clearanceBadge: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
    avatarLetter: 'MV',
  },
  {
    email: 'aris.thorne@semantiq.org',
    password: 'Password123!',
    name: 'Dr. Aris Thorne',
    title: 'Chief Technology Officer & System Admin',
    role: 'admin',
    clearance: 'Level 4 — RESTRICTED (Full)',
    clearanceBadge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    avatarLetter: 'AT',
  },
];

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please enter both your corporate email address and password.');
      return;
    }
    await executeLogin(email.trim(), password);
  };

  const executeLogin = async (userEmail: string, userPass: string) => {
    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await semantiqApi.login({ email: userEmail, password: userPass });
      onLoginSuccess({
        user_id: res.user_id,
        employee_id: res.employee_id,
        username: res.username,
        email: res.email,
        display_name: res.display_name,
        title: res.title,
        department: res.department,
        role: res.role,
        clearance_level: res.clearance_level,
        active: true,
      });
    } catch (err: any) {
      console.error('Authentication error:', err);
      const detail = err.response?.data?.detail;
      setErrorMessage(detail || 'Authentication failed. Please verify your credentials or contact administrator.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDevPersona = (persona: typeof SEED_PERSONAS[0]) => {
    setEmail(persona.email);
    setPassword(persona.password);
    executeLogin(persona.email, persona.password);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 selection:bg-indigo-500 selection:text-white relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-xl w-full space-y-6 z-10">
        {/* Brand Identity */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-indigo-300">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>SEMANTIQ • セマンティック — Enterprise Identity</span>
          </div>

          <h1 className="text-3xl font-black tracking-tight text-white font-mono">
            Sign In to SEMANTIQ
          </h1>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Zero-Trust Permission-Aware Organizational Knowledge Graph &amp; GraphRAG System.
          </p>
        </div>

        {/* Primary Login Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-sm space-y-5">
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-500/40 flex items-start space-x-3 text-xs text-rose-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 font-medium">
                Corporate Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="employee@semantiq.org"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5 font-medium">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-semibold flex items-center justify-center space-x-2 transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span className="flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              <span>HMAC-SHA256 Token Authority</span>
            </span>
            <span>Zero-Trust Pre-LLM</span>
          </div>
        </div>

        {/* Development Quick Sign-In (Demarcated for dev/testing only) */}
        <div className="border border-slate-800/60 bg-slate-900/40 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
              <Key className="w-3 h-3 text-amber-400" />
              <span>Development Quick Sign-In</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              Seeded Benchmark Accounts
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SEED_PERSONAS.map((p) => (
              <button
                key={p.email}
                type="button"
                onClick={() => handleSelectDevPersona(p)}
                disabled={loading}
                className="text-left p-2.5 rounded-xl bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700 transition-all flex items-center space-x-2.5 group"
              >
                <div className="w-7 h-7 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center font-mono font-bold text-xs text-indigo-300 group-hover:border-indigo-500/50">
                  {p.avatarLetter}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold text-white truncate font-mono">
                    {p.name}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate">
                    {p.role}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
