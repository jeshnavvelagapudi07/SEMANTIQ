import React, { useState, useEffect } from 'react';
import { UserRole, ClassificationLevel, UserProfile } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  Users,
  UserPlus,
  Shield,
  Key,
  Lock,
  Mail,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Edit2,
  UserX,
  UserCheck,
  X
} from 'lucide-react';

export const UserManagementView: React.FC = () => {
  const [employees, setEmployees] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editRoleUser, setEditRoleUser] = useState<UserProfile | null>(null);
  const [editClearanceUser, setEditClearanceUser] = useState<UserProfile | null>(null);

  // Form: Invite Employee
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteDept, setInviteDept] = useState('Engineering & Operations');
  const [inviteTitle, setInviteTitle] = useState('Systems Engineer');
  const [inviteRole, setInviteRole] = useState<UserRole>('operations_engineer');
  const [inviteClearance, setInviteClearance] = useState<ClassificationLevel>('CONFIDENTIAL');
  const [invitePassword, setInvitePassword] = useState('InitialPass2026!');
  const [inviteEmpId, setInviteEmpId] = useState('');

  // Form: Edit Role / Clearance
  const [newSelectedRole, setNewSelectedRole] = useState<UserRole>('operations_engineer');
  const [newSelectedClearance, setNewSelectedClearance] = useState<ClassificationLevel>('INTERNAL');
  const [mutationReason, setMutationReason] = useState('');

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const res = await semantiqApi.listEmployees();
      setEmployees(res.users || []);
    } catch (err: any) {
      console.error('Failed to load employee directory:', err);
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to fetch enterprise employee directory.' });
    } finally {
      setLoading(false);
    }
  };

  const handleInviteEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await semantiqApi.inviteEmployee({
        email: inviteEmail.trim().toLowerCase(),
        display_name: inviteName.trim(),
        department: inviteDept.trim(),
        job_title: inviteTitle.trim(),
        role: inviteRole,
        clearance_level: inviteClearance,
        initial_password: invitePassword,
        employee_id: inviteEmpId.trim() || undefined,
      });
      setStatusMessage({ type: 'success', text: `Employee profile created for ${inviteName}. Credentials provisioned.` });
      setShowInviteModal(false);
      resetInviteForm();
      await loadEmployees();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to invite employee.' });
    } finally {
      setLoading(false);
    }
  };

  const handleChangeRole = async () => {
    if (!editRoleUser) return;
    try {
      setLoading(true);
      await semantiqApi.changeUserRole(editRoleUser.id, newSelectedRole, mutationReason);
      setStatusMessage({ type: 'success', text: `Role updated for ${editRoleUser.display_name} to ${newSelectedRole}. Audited.` });
      setEditRoleUser(null);
      setMutationReason('');
      await loadEmployees();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Role change failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleChangeClearance = async () => {
    if (!editClearanceUser) return;
    try {
      setLoading(true);
      await semantiqApi.changeUserClearance(editClearanceUser.id, newSelectedClearance, mutationReason);
      setStatusMessage({ type: 'success', text: `Clearance updated for ${editClearanceUser.display_name} to ${newSelectedClearance}. Audited.` });
      setEditClearanceUser(null);
      setMutationReason('');
      await loadEmployees();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Clearance change failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (user: UserProfile) => {
    const nextStatus = user.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
    const actionDesc = nextStatus === 'DISABLED' ? 'revoke access and disable' : 'enable';
    if (!window.confirm(`Are you sure you want to ${actionDesc} the account for ${user.display_name}?`)) {
      return;
    }
    try {
      setLoading(true);
      await semantiqApi.changeUserStatus(user.id, nextStatus, `Account status set to ${nextStatus} by administrator.`);
      setStatusMessage({ type: 'success', text: `Account for ${user.display_name} is now ${nextStatus}.` });
      await loadEmployees();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.response?.data?.detail || 'Status transition failed.' });
    } finally {
      setLoading(false);
    }
  };

  const resetInviteForm = () => {
    setInviteEmail('');
    setInviteName('');
    setInviteDept('Engineering & Operations');
    setInviteTitle('Systems Engineer');
    setInviteRole('operations_engineer');
    setInviteClearance('CONFIDENTIAL');
    setInvitePassword('InitialPass2026!');
    setInviteEmpId('');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <Users className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-white font-mono">User Management &amp; Provisioning</h1>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-rose-950 border border-rose-500/40 text-rose-300">
              Admin Only
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-normal">
            Enterprise multi-employee identity directory, cryptographic credential provisioning, and role governance.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => { resetInviteForm(); setShowInviteModal(true); }}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Invite Employee</span>
          </button>
          <button
            onClick={loadEmployees}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notification banner */}
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

      {/* Employees Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 font-mono text-slate-400">
              <tr>
                <th className="py-3 px-4">Employee</th>
                <th className="py-3 px-4">Employee ID</th>
                <th className="py-3 px-4">Department &amp; Title</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Clearance</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {employees.map((emp) => (
                <tr key={emp.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-bold text-white">{emp.display_name}</div>
                    <div className="text-[11px] text-slate-400">{emp.email}</div>
                  </td>
                  <td className="py-3 px-4 font-bold text-indigo-300">{emp.employee_id}</td>
                  <td className="py-3 px-4">
                    <div className="text-slate-200">{emp.job_title}</div>
                    <div className="text-[10px] text-slate-500">{emp.department}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30 text-indigo-300 uppercase">
                      {emp.role}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${
                      emp.clearance_level === 'RESTRICTED' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
                      emp.clearance_level === 'CONFIDENTIAL' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
                      'bg-slate-500/20 text-slate-300 border-slate-500/40'
                    }`}>
                      {emp.clearance_level}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-[10px] px-2 py-0.5 rounded ${
                      emp.status === 'ACTIVE'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : 'bg-rose-500/20 text-rose-300'
                    }`}>
                      {emp.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => {
                          setEditRoleUser(emp);
                          setNewSelectedRole(emp.role);
                          setMutationReason('');
                        }}
                        className="p-1 rounded text-slate-400 hover:text-indigo-300 hover:bg-slate-800 transition-colors"
                        title="Modify Role"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => {
                          setEditClearanceUser(emp);
                          setNewSelectedClearance(emp.clearance_level);
                          setMutationReason('');
                        }}
                        className="p-1 rounded text-slate-400 hover:text-amber-300 hover:bg-slate-800 transition-colors"
                        title="Modify Clearance"
                      >
                        <Shield className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleToggleStatus(emp)}
                        className={`p-1 rounded transition-colors ${
                          emp.status === 'ACTIVE'
                            ? 'text-slate-400 hover:text-rose-400 hover:bg-rose-950/30'
                            : 'text-slate-400 hover:text-emerald-400 hover:bg-emerald-950/30'
                        }`}
                        title={emp.status === 'ACTIVE' ? 'Disable Account' : 'Enable Account'}
                      >
                        {emp.status === 'ACTIVE' ? <UserX className="w-3.5 h-3.5" /> : <UserCheck className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {employees.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">
                    No employees found in directory.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Invite Employee */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-mono">Provision New Employee</h3>
              <button onClick={() => setShowInviteModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleInviteEmployee} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Corporate Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="daiki.tanaka@semantiq.org"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Full Legal Name</label>
                <input
                  type="text"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  placeholder="Daiki Tanaka"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">Department</label>
                  <input
                    type="text"
                    value={inviteDept}
                    onChange={(e) => setInviteDept(e.target.value)}
                    placeholder="Reliability & Ops"
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Job Title</label>
                  <input
                    type="text"
                    value={inviteTitle}
                    onChange={(e) => setInviteTitle(e.target.value)}
                    placeholder="Lead Cryo Specialist"
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">Assigned Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as UserRole)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
                  >
                    <option value="operations_engineer">Operations Engineer</option>
                    <option value="project_manager">Project Manager</option>
                    <option value="viewer">Viewer / Auditor</option>
                    <option value="admin">Administrator</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Clearance Level</label>
                  <select
                    value={inviteClearance}
                    onChange={(e) => setInviteClearance(e.target.value as ClassificationLevel)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
                  >
                    <option value="PUBLIC">PUBLIC (Level 1)</option>
                    <option value="INTERNAL">INTERNAL (Level 2)</option>
                    <option value="CONFIDENTIAL">CONFIDENTIAL (Level 3)</option>
                    <option value="RESTRICTED">RESTRICTED (Level 4)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Initial Temporary Password</label>
                <input
                  type="password"
                  value={invitePassword}
                  onChange={(e) => setInvitePassword(e.target.value)}
                  placeholder="Min 6 characters"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 font-semibold"
                >
                  Provision Employee
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit Role */}
      {editRoleUser && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 font-mono text-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white">Modify Role: {editRoleUser.display_name}</h3>
              <button onClick={() => setEditRoleUser(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">New Role</label>
              <select
                value={newSelectedRole}
                onChange={(e) => setNewSelectedRole(e.target.value as UserRole)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
              >
                <option value="operations_engineer">Operations Engineer</option>
                <option value="project_manager">Project Manager</option>
                <option value="viewer">Viewer / Auditor</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Audit Justification Reason</label>
              <input
                type="text"
                value={mutationReason}
                onChange={(e) => setMutationReason(e.target.value)}
                placeholder="Department reassignment or promotion..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setEditRoleUser(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleChangeRole}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-500"
              >
                Save Role Change
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Edit Clearance */}
      {editClearanceUser && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 font-mono text-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white">Modify Clearance: {editClearanceUser.display_name}</h3>
              <button onClick={() => setEditClearanceUser(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">New Clearance Level</label>
              <select
                value={newSelectedClearance}
                onChange={(e) => setNewSelectedClearance(e.target.value as ClassificationLevel)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none"
              >
                <option value="PUBLIC">PUBLIC (Level 1)</option>
                <option value="INTERNAL">INTERNAL (Level 2)</option>
                <option value="CONFIDENTIAL">CONFIDENTIAL (Level 3)</option>
                <option value="RESTRICTED">RESTRICTED (Level 4)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Audit Justification Reason</label>
              <input
                type="text"
                value={mutationReason}
                onChange={(e) => setMutationReason(e.target.value)}
                placeholder="Project NDA signed / security vetted..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setEditClearanceUser(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleChangeClearance}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-500"
              >
                Save Clearance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
