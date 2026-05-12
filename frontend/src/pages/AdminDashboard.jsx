/**
 * AdminDashboard.jsx
 * Sidebar nav: Overview, Users, Alert Log, Retraining.
 * Header bar with DB/RF/GB health status indicators.
 */

import { useState, useEffect } from 'react';
import {
  LayoutDashboard, Users, Bell, RefreshCw, LogOut,
  Plus, X, CheckCircle, XCircle, Loader2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';
import AlertLog from '../components/AlertLog.jsx';
import RetrainingPanel from '../components/RetrainingPanel.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-white rounded border border-slate-200 px-4 py-3">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color: color || '#1e293b' }}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ─── Health indicator ─────────────────────────────────────────────────────────
function HealthDot({ label, ok }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {ok === null ? (
        <Loader2 size={10} className="animate-spin text-slate-400" />
      ) : ok ? (
        <CheckCircle size={10} className="text-emerald-500" />
      ) : (
        <XCircle size={10} className="text-red-500" />
      )}
      <span className="text-slate-600">{label}</span>
    </div>
  );
}

const SEVERITY_COLORS = {
  None: '#10b981', Mild: '#f59e0b', Moderate: '#f97316', Severe: '#ef4444',
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'admin';

  const [view, setView] = useState('overview');
  const [health, setHealth] = useState({ db: null, rf: null, gb: null });
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [showCreatePanel, setShowCreatePanel] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'patient' });
  const [createError, setCreateError] = useState(null);
  const [createLoading, setCreateLoading] = useState(false);

  // Fetch health status
  useEffect(() => {
    client.get('/health')
      .then((res) => {
        const d = res.data;
        setHealth({
          db: d.db === true,
          rf: d.models?.rf_classifier === true,
          gb: d.models?.gb_severity === true,
        });
      })
      .catch(() => setHealth({ db: false, rf: false, gb: false }));
  }, []);

  // Fetch stats
  useEffect(() => {
    if (view === 'overview') {
      client.get('/api/stats').then((res) => setStats(res.data)).catch(() => {});
    }
  }, [view]);

  // Fetch users
  useEffect(() => {
    if (view === 'users') {
      client.get('/api/users').then((res) => setUsers(res.data?.users || [])).catch(() => {});
    }
  }, [view]);

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  async function handleDeactivate(userId) {
    try {
      await client.patch(`/api/users/${userId}/deactivate`);
      setUsers((prev) => prev.map((u) => u.user_id === userId ? { ...u, status: 'inactive' } : u));
    } catch {
      // silently fail
    }
  }

  async function handleCreateUser(e) {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError(null);
    try {
      const res = await client.post('/api/users', newUser);
      setUsers((prev) => [...prev, res.data?.user || newUser]);
      setShowCreatePanel(false);
      setNewUser({ username: '', email: '', password: '', role: 'patient' });
    } catch (err) {
      setCreateError(err.response?.data?.message || 'Failed to create user.');
    } finally {
      setCreateLoading(false);
    }
  }

  const filteredUsers = users.filter((u) =>
    u.username?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.email?.toLowerCase().includes(userSearch.toLowerCase())
  );

  const initials = username.slice(0, 2).toUpperCase();

  const NAV_ITEMS = [
    { id: 'overview',    label: 'Overview',   Icon: LayoutDashboard },
    { id: 'users',       label: 'Users',      Icon: Users },
    { id: 'alertlog',    label: 'Alert Log',  Icon: Bell },
    { id: 'retraining',  label: 'Retraining', Icon: RefreshCw },
  ];

  // Chart data from stats
  const areaData = stats?.daily_predictions || [];
  const severityPieData = stats?.severity_distribution
    ? Object.entries(stats.severity_distribution).map(([name, value]) => ({ name, value }))
    : [];
  const typePieData = stats?.type_distribution
    ? Object.entries(stats.type_distribution).map(([name, value]) => ({ name, value }))
    : [];

  const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Sidebar */}
      <div className="flex flex-col flex-shrink-0" style={{ width: '220px', backgroundColor: '#0f1117' }}>
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded flex items-center justify-center text-white font-bold text-xs" style={{ backgroundColor: '#6366f1' }}>A</div>
            <span className="text-white font-semibold text-sm tracking-tight">AnemiaDetect</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV_ITEMS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setView(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-all border-l-2 ${
                view === id
                  ? 'text-white border-indigo-500'
                  : 'text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-800'
              }`}
              style={view === id ? { backgroundColor: 'rgba(99,102,241,0.15)' } : {}}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-800 space-y-3">
          <LanguageSelector />
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ backgroundColor: '#6366f1' }}>
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">{username}</p>
              <p className="text-slate-500 text-xs">Admin</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-300 transition" title="Logout">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#f8f9fa' }}>
        {/* Header bar with health indicators */}
        <div className="h-12 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
          <h2 className="text-sm font-semibold text-slate-700">
            {view === 'overview' && 'Overview'}
            {view === 'users' && 'User Management'}
            {view === 'alertlog' && 'Alert Log'}
            {view === 'retraining' && 'Model Retraining'}
          </h2>
          <div className="flex items-center gap-4">
            <HealthDot label="DB" ok={health.db} />
            <HealthDot label="RF" ok={health.rf} />
            <HealthDot label="GB" ok={health.gb} />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* Overview */}
          {view === 'overview' && (
            <div className="space-y-5">
              {/* Stat cards */}
              <div className="grid grid-cols-3 gap-4">
                <StatCard label="Total Predictions" value={stats?.total_predictions} />
                <StatCard label="Total Users" value={stats?.total_users} />
                <StatCard label="Anemia Cases" value={stats?.anemia_cases} color="#ef4444" />
                <StatCard label="Severe Cases" value={stats?.severe_cases} color="#ef4444" sub="HGB < 8.0" />
                <StatCard label="Alerts Sent" value={stats?.alerts_sent} />
                <StatCard label="Retraining Runs" value={stats?.retrain_count} />
              </div>

              {/* Area chart */}
              {areaData.length > 0 && (
                <div className="bg-white rounded border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Daily Predictions</p>
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

              {/* Pie charts */}
              <div className="grid grid-cols-2 gap-4">
                {severityPieData.length > 0 && (
                  <div className="bg-white rounded border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Severity Distribution</p>
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={severityPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                          {severityPieData.map((entry, idx) => (
                            <Cell key={idx} fill={SEVERITY_COLORS[entry.name] || PIE_COLORS[idx % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
                {typePieData.length > 0 && (
                  <div className="bg-white rounded border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Anemia Type Distribution</p>
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={typePieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                          {typePieData.map((entry, idx) => (
                            <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Users */}
          {view === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search users..."
                  className="flex-1 rounded border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                />
                <button
                  onClick={() => setShowCreatePanel(true)}
                  className="flex items-center gap-1.5 text-white font-semibold px-3 py-2 rounded text-sm transition"
                  style={{ backgroundColor: '#6366f1' }}
                >
                  <Plus size={14} />
                  Create User
                </button>
              </div>

              <div className="bg-white rounded border border-slate-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    <tr>
                      <th className="px-3 py-2 text-left">Username</th>
                      <th className="px-3 py-2 text-left">Email</th>
                      <th className="px-3 py-2 text-left">Role</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {filteredUsers.map((u) => (
                      <tr key={u.user_id} className="hover:bg-slate-50 transition" style={{ height: '36px' }}>
                        <td className="px-3 py-1.5 font-medium text-slate-700">{u.username}</td>
                        <td className="px-3 py-1.5 text-slate-500 text-xs">{u.email}</td>
                        <td className="px-3 py-1.5">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">{u.role}</span>
                        </td>
                        <td className="px-3 py-1.5">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${u.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                            {u.status}
                          </span>
                        </td>
                        <td className="px-3 py-1.5">
                          {u.status === 'active' && (
                            <button
                              onClick={() => handleDeactivate(u.user_id)}
                              className="text-xs text-red-600 hover:text-red-800 transition font-medium"
                            >
                              Deactivate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Create User slide-in panel */}
              {showCreatePanel && (
                <>
                  <div className="fixed inset-0 bg-black/20 z-40" onClick={() => setShowCreatePanel(false)} />
                  <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-2xl z-50 flex flex-col">
                    <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                      <h3 className="font-semibold text-slate-800">Create User</h3>
                      <button onClick={() => setShowCreatePanel(false)} className="text-slate-400 hover:text-slate-600 transition">
                        <X size={18} />
                      </button>
                    </div>
                    <form onSubmit={handleCreateUser} className="flex-1 p-5 space-y-4">
                      {[
                        { name: 'username', label: 'Username', type: 'text' },
                        { name: 'email', label: 'Email', type: 'email' },
                        { name: 'password', label: 'Password', type: 'password' },
                      ].map(({ name, label, type }) => (
                        <div key={name}>
                          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">{label}</label>
                          <input
                            type={type}
                            value={newUser[name]}
                            onChange={(e) => setNewUser((p) => ({ ...p, [name]: e.target.value }))}
                            required
                            className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:border-transparent transition"
                          />
                        </div>
                      ))}
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Role</label>
                        <select
                          value={newUser.role}
                          onChange={(e) => setNewUser((p) => ({ ...p, role: e.target.value }))}
                          className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:border-transparent transition"
                        >
                          <option value="patient">Patient</option>
                          <option value="doctor">Doctor</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>
                      {createError && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{createError}</div>}
                      <button
                        type="submit"
                        disabled={createLoading}
                        className="w-full text-white font-semibold py-2 rounded text-sm transition disabled:opacity-60"
                        style={{ backgroundColor: '#6366f1' }}
                      >
                        {createLoading ? 'Creating...' : 'Create User'}
                      </button>
                    </form>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Alert Log */}
          {view === 'alertlog' && <AlertLog />}

          {/* Retraining */}
          {view === 'retraining' && <RetrainingPanel />}
        </div>
      </div>
    </div>
  );
}
