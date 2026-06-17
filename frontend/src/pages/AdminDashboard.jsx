/**
 * AdminDashboard.jsx
 * Admin dashboard with system health, user management, and analytics.
 */

import { useState, useEffect } from 'react';
import {
  Home, Users, RefreshCw, Bell, Layers, Calendar, Server,
  LogOut, Plus, X, CheckCircle, XCircle, Loader2, BarChart3, Settings,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';

import AlertLog from '../components/AlertLog.jsx';
import RetrainingPanel from '../components/RetrainingPanel.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';
import ModelComparison from '../components/ModelComparison.jsx';
import AnalyticsDashboard from '../components/AnalyticsDashboard.jsx';
import ProfileSettings from '../components/ProfileSettings.jsx';
import NotificationBell from '../components/NotificationBell.jsx';
import ThemeToggle from '../components/ThemeToggle.jsx';
import Breadcrumb from '../components/Breadcrumb.jsx';
import StatusFooter from '../components/StatusFooter.jsx';

function HealthDot({ label, ok }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {ok === null ? <Loader2 size={10} className="animate-spin text-slate-400" /> : ok ? <CheckCircle size={10} className="text-emerald-500" /> : <XCircle size={10} className="text-red-500" />}
      <span className="text-slate-600">{label}</span>
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 shadow-md hover:scale-[1.02] transition-transform">
      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color: color || '#1e293b' }}>{value ?? 0}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

const SEVERITY_COLORS = { None: '#10b981', Mild: '#f59e0b', Moderate: '#f97316', Severe: '#ef4444' };
const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function AdminScheduleAppointment() {
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [form, setForm] = useState({ doctor_id: '', patient_id: '', slot_date: '', slot_time: '' });
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    client.get('/api/users').then(res => {
      const all = res.data?.users || [];
      setDoctors(all.filter(u => u.role === 'doctor' && u.status === 'active'));
      setPatients(all.filter(u => u.role === 'patient' && u.status === 'active'));
    }).catch(() => {});
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setMsg(null);
    try {
      await client.post('/api/appointments/request', {
        doctor_id: parseInt(form.doctor_id),
        patient_id: parseInt(form.patient_id),
        slot_date: form.slot_date,
        slot_time: form.slot_time,
      });
      setMsg('Appointment scheduled (confirmed)');
      setForm({ doctor_id: '', patient_id: '', slot_date: '', slot_time: '' });
    } catch (err) {
      setMsg(err.response?.data?.message || 'Failed');
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Schedule Appointment</h2>
      <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4 shadow-md">
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Doctor</label>
          <select value={form.doctor_id} onChange={e => setForm(f => ({ ...f, doctor_id: e.target.value }))} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">Select doctor...</option>
            {doctors.map(d => <option key={d.user_id} value={d.user_id}>{d.username}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Patient</label>
          <select value={form.patient_id} onChange={e => setForm(f => ({ ...f, patient_id: e.target.value }))} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">Select patient...</option>
            {patients.map(p => <option key={p.user_id} value={p.user_id}>{p.username}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Date</label>
            <input type="date" value={form.slot_date} onChange={e => setForm(f => ({ ...f, slot_date: e.target.value }))} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Time</label>
            <input type="time" value={form.slot_time} onChange={e => setForm(f => ({ ...f, slot_time: e.target.value }))} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>
        {msg && <p className={`text-sm ${msg.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>{msg}</p>}
        <button type="submit" className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-semibold py-2 rounded-lg text-sm hover:opacity-90 transition">
          Schedule (Auto-Confirm)
        </button>
      </form>
    </div>
  );
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'admin';

  const [view, setView] = useState('overview');
  const [health, setHealth] = useState({ db: null, rf: null, gb: null, ws: null, queue: null });
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [showCreatePanel, setShowCreatePanel] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'patient' });
  const [createError, setCreateError] = useState(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [badges, setBadges] = useState({});

  useEffect(() => {
    client.get('/health').then(res => {
      const d = res.data;
      setHealth({ db: d.db === true, rf: d.models?.rf_classifier === true, gb: d.models?.gb_severity === true, ws: true, queue: true });
    }).catch(() => setHealth({ db: false, rf: false, gb: false, ws: false, queue: false }));
  }, []);

  useEffect(() => {
    if (view === 'overview') {
      client.get('/api/stats').then(res => {
        const s = res.data?.stats || res.data || {};
        // Map backend field names to what the overview expects
        setStats({
          total_predictions: s.total_predictions || 0,
          total_users: (s.users_by_role?.patient || 0) + (s.users_by_role?.doctor || 0) + (s.users_by_role?.admin || 0),
          anemia_cases: Object.entries(s.predictions_by_severity || {}).filter(([k]) => k !== 'None').reduce((sum, [, v]) => sum + v, 0),
          severe_cases: s.predictions_by_severity?.Severe || 0,
          alerts_sent: s.total_alerts_sent || 0,
          retrain_count: s.retrain_count || 0,
          active_doctors: s.users_by_role?.doctor || 0,
          avg_adherence: s.avg_adherence || null,
          severity_distribution: s.predictions_by_severity || {},
          type_distribution: s.predictions_by_type || {},
          daily_predictions: s.predictions_per_day || [],
        });
      }).catch(() => setStats({}));
    }
  }, [view]);

  useEffect(() => {
    if (view === 'users') {
      client.get('/api/users').then(res => setUsers(res.data?.users || [])).catch(() => {});
    }
  }, [view]);

  useEffect(() => {
    client.get('/api/notifications/unread-count').then(r => setBadges(b => ({ ...b, alerts: r.data?.count || 0 }))).catch(() => {});
  }, []);

  const NAV_ITEMS = [
    { id: 'overview', label: 'Overview', Icon: Home },
    { id: 'users', label: 'Users', Icon: Users },
    { id: 'schedule', label: 'Schedule Appt', Icon: Calendar },
    { id: 'analytics', label: 'Analytics', Icon: BarChart3 },
    { id: 'alertlog', label: 'Alert Log', Icon: Bell, badge: badges.alerts, badgeColor: '#ef4444' },
    { id: 'comparison', label: 'Model Comparison', Icon: Layers },
    { id: 'retraining', label: 'Retraining', Icon: RefreshCw },
    { id: 'health', label: 'System Health', Icon: Server },
    { id: 'settings', label: 'Settings', Icon: Settings },
  ];

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  async function handleDeactivate(userId) {
    try {
      await client.patch(`/api/users/${userId}/deactivate`);
      setUsers(prev => prev.map(u => u.user_id === userId ? { ...u, status: 'inactive' } : u));
    } catch {}
  }

  async function handleReactivate(userId) {
    try {
      await client.patch(`/api/users/${userId}/reactivate`);
      setUsers(prev => prev.map(u => u.user_id === userId ? { ...u, status: 'active' } : u));
    } catch {}
  }

  async function handleCreateUser(e) {
    e.preventDefault();
    setCreateLoading(true); setCreateError(null);
    try {
      const res = await client.post('/api/users', newUser);
      setUsers(prev => [...prev, res.data?.user || newUser]);
      setShowCreatePanel(false);
      setNewUser({ username: '', email: '', password: '', role: 'patient' });
    } catch (err) { setCreateError(err.response?.data?.message || 'Failed to create user.'); }
    finally { setCreateLoading(false); }
  }

  const filteredUsers = users.filter(u => u.username?.toLowerCase().includes(userSearch.toLowerCase()) || u.email?.toLowerCase().includes(userSearch.toLowerCase()));
  const initials = username.slice(0, 2).toUpperCase();
  const activeLabel = NAV_ITEMS.find(n => n.id === view)?.label || 'Overview';

  const areaData = stats?.daily_predictions || [];
  const severityPieData = stats?.severity_distribution ? Object.entries(stats.severity_distribution).map(([name, value]) => ({ name, value })) : [];
  const typePieData = stats?.type_distribution ? Object.entries(stats.type_distribution).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Sidebar */}
      <div className="flex flex-col flex-shrink-0" style={{ width: '220px', backgroundColor: '#0f1117' }}>
        <div className="px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded flex items-center justify-center text-white font-bold text-xs" style={{ backgroundColor: '#6366f1' }}>A</div>
            <span className="text-white font-semibold text-sm tracking-tight">AnemiaCare</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ id, label, Icon, badge, badgeColor }) => (
            <button
              key={id}
              onClick={() => setView(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-all ${
                view === id ? 'text-white bg-indigo-500/15 border-l-2 border-indigo-500' : 'text-slate-400 border-l-2 border-transparent hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Icon size={15} />
              <span className="flex-1 text-left truncate">{label}</span>
              {badge > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white min-w-[18px] text-center" style={{ backgroundColor: badgeColor || '#ef4444' }}>
                  {badge}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="px-3 py-3 border-t border-slate-800 space-y-2">
          <LanguageSelector />
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: '#6366f1' }}>{initials}</div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">{username}</p>
              <p className="text-slate-500 text-[10px]">Admin</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-300" title="Logout"><LogOut size={14} /></button>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
        {/* Header */}
        <div className="h-12 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-5 flex-shrink-0">
          <Breadcrumb items={['Admin', activeLabel]} />
          <div className="flex items-center gap-4">
            <HealthDot label="DB" ok={health.db} />
            <HealthDot label="Models" ok={health.rf && health.gb} />
            <ThemeToggle />
            <NotificationBell />
          </div>
        </div>

        {/* Content */}
        <div id="main-content" className="flex-1 overflow-y-auto p-5">
          {/* Overview */}
          {view === 'overview' && (
            <div className="space-y-5">
              {/* 8 stat cards in 2 rows */}
              <div className="grid grid-cols-4 gap-4">
                <StatCard label="Total Predictions" value={stats?.total_predictions ?? 0} />
                <StatCard label="Total Users" value={stats?.total_users ?? 0} />
                <StatCard label="Anemia Cases" value={stats?.anemia_cases ?? 0} color="#ef4444" />
                <StatCard label="Severe Cases" value={stats?.severe_cases ?? 0} color="#ef4444" sub="HGB < 8.0" />
                <StatCard label="Alerts Sent" value={stats?.alerts_sent ?? 0} />
                <StatCard label="Retraining Runs" value={stats?.retrain_count ?? 0} />
                <StatCard label="Active Doctors" value={stats?.active_doctors ?? 0} color="#6366f1" />
                <StatCard label="Avg Adherence" value={stats?.avg_adherence ? `${stats.avg_adherence}%` : '0%'} color="#10b981" />
              </div>

              {/* Full-width area chart */}
              {areaData.length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Daily Predictions (30 days)</p>
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={areaData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
                      <Tooltip />
                      <Area type="monotone" dataKey="count" stroke="#6366f1" fill="#e0e7ff" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* 3-column chart row */}
              <div className="grid grid-cols-3 gap-4">
                {severityPieData.length > 0 && (
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Severity</p>
                    <ResponsiveContainer width="100%" height={160}>
                      <PieChart>
                        <Pie data={severityPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={55} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={9}>
                          {severityPieData.map((entry, idx) => <Cell key={idx} fill={SEVERITY_COLORS[entry.name] || PIE_COLORS[idx % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
                {typePieData.length > 0 && (
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Anemia Types</p>
                    <ResponsiveContainer width="100%" height={160}>
                      <PieChart>
                        <Pie data={typePieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={55} label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={9}>
                          {typePieData.map((_, idx) => <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip />
                        <Legend iconSize={8} wrapperStyle={{ fontSize: '9px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
                {areaData.length > 0 && (
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Weekly Volume</p>
                    <ResponsiveContainer width="100%" height={160}>
                      <BarChart data={areaData.slice(-7)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} />
                        <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* System Health */}
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase mb-3">System Health</p>
                <div className="grid grid-cols-4 gap-4">
                  <div className="flex items-center gap-2"><HealthDot label="Database" ok={health.db} /></div>
                  <div className="flex items-center gap-2"><HealthDot label="RF Model" ok={health.rf} /></div>
                  <div className="flex items-center gap-2"><HealthDot label="GB Model" ok={health.gb} /></div>
                  <div className="flex items-center gap-2"><HealthDot label="WebSocket" ok={health.ws} /></div>
                </div>
              </div>
            </div>
          )}

          {/* Users */}
          {view === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <input type="text" value={userSearch} onChange={e => setUserSearch(e.target.value)} placeholder="Search users..." className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <button onClick={() => setShowCreatePanel(true)} className="flex items-center gap-1.5 text-white font-semibold px-3 py-2 rounded-lg text-sm bg-indigo-500 hover:bg-indigo-600 transition">
                  <Plus size={14} /> Create User
                </button>
              </div>
              <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                    <tr>
                      <th className="px-3 py-2 text-left">Username</th>
                      <th className="px-3 py-2 text-left">Email</th>
                      <th className="px-3 py-2 text-left">Role</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {filteredUsers.map(u => (
                      <tr key={u.user_id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium text-slate-700">{u.username}</td>
                        <td className="px-3 py-2 text-slate-500 text-xs">{u.email}</td>
                        <td className="px-3 py-2"><span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">{u.role}</span></td>
                        <td className="px-3 py-2"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${u.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{u.status}</span></td>
                        <td className="px-3 py-2">
                          {u.status === 'active' && <button onClick={() => handleDeactivate(u.user_id)} className="text-xs text-red-600 hover:text-red-800 font-medium">Deactivate</button>}
                          {u.status === 'inactive' && <button onClick={() => handleReactivate(u.user_id)} className="text-xs text-green-600 hover:text-green-800 font-medium">Reactivate</button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Create User Modal — centered overlay */}
              {showCreatePanel && (
                <>
                  <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setShowCreatePanel(false)} />
                  <div className="fixed inset-0 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-2xl w-96 flex flex-col">
                      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                        <h3 className="font-semibold text-slate-800">Create User</h3>
                        <button onClick={() => setShowCreatePanel(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
                      </div>
                      <form onSubmit={handleCreateUser} className="p-5 space-y-4">
                        {[{ name: 'username', label: 'Username', type: 'text' }, { name: 'email', label: 'Email', type: 'email' }, { name: 'password', label: 'Password', type: 'password' }].map(({ name, label, type }) => (
                          <div key={name}>
                            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">{label}</label>
                            <input type={type} value={newUser[name]} onChange={e => setNewUser(p => ({ ...p, [name]: e.target.value }))} required className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                          </div>
                        ))}
                        <div>
                          <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Role</label>
                          <select value={newUser.role} onChange={e => setNewUser(p => ({ ...p, role: e.target.value }))} className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                            <option value="patient">Patient</option>
                            <option value="doctor">Doctor</option>
                            <option value="admin">Admin</option>
                          </select>
                        </div>
                        {createError && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{createError}</div>}
                        <button type="submit" disabled={createLoading} className="w-full bg-indigo-500 text-white font-semibold py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60">
                          {createLoading ? 'Creating...' : 'Create User'}
                        </button>
                      </form>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {view === 'schedule' && <AdminScheduleAppointment />}
          {view === 'analytics' && <AnalyticsDashboard />}
          {view === 'comparison' && <ModelComparison />}
          {view === 'retraining' && <RetrainingPanel />}
          {view === 'alertlog' && <AlertLog />}
          {view === 'health' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-800">System Health</h2>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Database', ok: health.db, desc: 'SQLite connection' },
                  { label: 'RF Classifier', ok: health.rf, desc: 'Random Forest model loaded' },
                  { label: 'GB Severity', ok: health.gb, desc: 'Gradient Boosting model loaded' },
                  { label: 'WebSocket', ok: health.ws, desc: 'Real-time connections' },
                ].map(item => (
                  <div key={item.label} className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-3">
                    {item.ok ? <CheckCircle size={20} className="text-emerald-500" /> : <XCircle size={20} className="text-red-500" />}
                    <div>
                      <p className="text-sm font-medium text-slate-700">{item.label}</p>
                      <p className="text-xs text-slate-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {view === 'settings' && <ProfileSettings />}
        </div>

        <StatusFooter />
      </div>
    </div>
  );
}
