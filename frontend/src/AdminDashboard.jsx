import { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const API_BASE = 'http://127.0.0.1:5000';

export default function AdminDashboard() {
  // ─── State Management ──────────────────────────────────────────────────────
  const [stats, setStats] = useState({
    total_patients: 0,
    high_risk_count: 0,
    moderate_risk_count: 0,
    low_risk_count: 0,
    cbc_tests: 0,
    triage_tests: 0,
  });
  
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userError, setUserError] = useState(null);
  const [userSuccess, setUserSuccess] = useState(null);
  
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    password: '',
    role: 'doctor',
  });
  
  const [creatingUser, setCreatingUser] = useState(false);

  // ─── Fetch Data on Mount ──────────────────────────────────────────────────
  useEffect(() => {
    fetchStats();
    fetchUsers();
  }, []);

  async function fetchStats() {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/api/stats`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to fetch stats');
      setStats(data.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchUsers() {
    try {
      const response = await fetch(`${API_BASE}/api/users`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to fetch users');
      setUsers(data.data || []);
    } catch (err) {
      setUserError(err.message);
    }
  }

  // ─── User Management Handlers ──────────────────────────────────────────────
  function handleNewUserChange(e) {
    const { name, value } = e.target;
    setNewUser(prev => ({ ...prev, [name]: value }));
  }

  async function handleCreateUser(e) {
    e.preventDefault();
    setUserError(null);
    setUserSuccess(null);

    // Validation
    if (!newUser.username.trim()) {
      setUserError('Username is required');
      return;
    }
    if (newUser.username.length < 3) {
      setUserError('Username must be at least 3 characters');
      return;
    }
    if (!newUser.password) {
      setUserError('Password is required');
      return;
    }
    if (newUser.password.length < 6) {
      setUserError('Password must be at least 6 characters');
      return;
    }
    if (!newUser.email.trim()) {
      setUserError('Email is required');
      return;
    }

    setCreatingUser(true);
    try {
      const response = await fetch(`${API_BASE}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);

      setUserSuccess(`User ${newUser.username} created successfully!`);
      setNewUser({ username: '', email: '', password: '', role: 'doctor' });
      
      // Refresh users list
      fetchUsers();
      
      // Clear success message after 3 seconds
      setTimeout(() => setUserSuccess(null), 3000);
    } catch (err) {
      setUserError(err.message);
    } finally {
      setCreatingUser(false);
    }
  }

  async function handleDeleteUser(userId, username) {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/users/${userId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);

      setUserSuccess(`User ${username} deleted successfully`);
      fetchUsers();
      setTimeout(() => setUserSuccess(null), 3000);
    } catch (err) {
      setUserError(err.message);
    }
  }

  // ─── Data for Charts ──────────────────────────────────────────────────────
  const riskDistributionData = [
    { name: 'Low Risk', value: stats.low_risk_count, color: '#10b981' },
    { name: 'Moderate Risk', value: stats.moderate_risk_count, color: '#f59e0b' },
    { name: 'High Risk', value: stats.high_risk_count, color: '#ef4444' },
  ];

  const testComparisonData = [
    {
      name: 'Tests',
      'Triage Tests': stats.triage_tests,
      'CBC Scans': stats.cbc_tests,
    },
  ];

  // ─── Summary Cards Component ──────────────────────────────────────────────
  const SummaryCard = ({ label, value, icon, bgColor }) => (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            {label}
          </p>
          <p className="text-3xl font-bold text-slate-800">{value}</p>
        </div>
        <div className={`${bgColor} rounded-full p-3 text-2xl`}>
          {icon}
        </div>
      </div>
    </div>
  );

  // ─── Loading State ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500">
        <div className="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        <p className="mt-3">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-slate-50 overflow-y-auto h-full">
      {/* ════════════════════════════════════════════════════════════════════════
          HEADER
      ════════════════════════════════════════════════════════════════════════ */}
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Admin Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">System analytics, patient data, and user management</p>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          ERROR & SUCCESS MESSAGES
      ════════════════════════════════════════════════════════════════════════ */}
      {error && (
        <div className="bg-red-50 border border-red-300 text-red-700 rounded-lg px-5 py-4 text-sm flex items-start gap-3">
          <span>⚠️</span>
          <div>
            <p className="font-semibold">Failed to load analytics</p>
            <p className="text-red-600 text-xs mt-1">{error}</p>
          </div>
        </div>
      )}

      {userError && (
        <div className="bg-red-50 border border-red-300 text-red-700 rounded-lg px-5 py-4 text-sm flex items-center gap-2">
          <span>⚠️</span> {userError}
        </div>
      )}

      {userSuccess && (
        <div className="bg-green-50 border border-green-300 text-green-700 rounded-lg px-5 py-4 text-sm flex items-center gap-2">
          <span>✅</span> {userSuccess}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          ANALYTICS SECTION: SUMMARY CARDS
      ════════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          label="Total Patients"
          value={stats.total_patients}
          icon="👥"
          bgColor="bg-blue-100"
        />
        <SummaryCard
          label="High Risk Cases"
          value={stats.high_risk_count}
          icon="🔴"
          bgColor="bg-red-100"
        />
        <SummaryCard
          label="Moderate Risk"
          value={stats.moderate_risk_count}
          icon="🟡"
          bgColor="bg-yellow-100"
        />
        <SummaryCard
          label="Safe Cases"
          value={stats.low_risk_count}
          icon="🟢"
          bgColor="bg-green-100"
        />
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          CHARTS SECTION
      ════════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart: Risk Distribution */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 overflow-hidden">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-800">Risk Distribution</h2>
            <p className="text-xs text-slate-500 mt-1">Patient risk category breakdown</p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={riskDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {riskDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart: Test Comparison */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 overflow-hidden">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-800">Test Volume</h2>
            <p className="text-xs text-slate-500 mt-1">Triage assessments vs CBC scans performed</p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={testComparisonData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                }}
              />
              <Legend />
              <Bar dataKey="Triage Tests" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              <Bar dataKey="CBC Scans" fill="#10b981" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          USER MANAGEMENT SECTION
      ════════════════════════════════════════════════════════════════════════ */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {/* Header with Create User Form */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">User Management</h2>
              <p className="text-xs text-slate-500 mt-1">{users.length} user{users.length !== 1 ? 's' : ''} in system</p>
            </div>

            {/* Inline Create User Form */}
            <form onSubmit={handleCreateUser} className="flex gap-2 flex-wrap">
              <input
                type="text"
                name="username"
                value={newUser.username}
                onChange={handleNewUserChange}
                placeholder="Username"
                className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <input
                type="email"
                name="email"
                value={newUser.email}
                onChange={handleNewUserChange}
                placeholder="Email"
                className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <input
                type="password"
                name="password"
                value={newUser.password}
                onChange={handleNewUserChange}
                placeholder="Password"
                className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <select
                name="role"
                value={newUser.role}
                onChange={handleNewUserChange}
                className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="doctor">Doctor</option>
                <option value="admin">Admin</option>
              </select>
              <button
                type="submit"
                disabled={creatingUser}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium transition"
              >
                {creatingUser ? 'Creating…' : 'Create User'}
              </button>
            </form>
          </div>
        </div>

        {/* Users Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wide">
              <tr>
                <th className="px-6 py-4 whitespace-nowrap">ID</th>
                <th className="px-6 py-4 whitespace-nowrap">Username</th>
                <th className="px-6 py-4 whitespace-nowrap">Email</th>
                <th className="px-6 py-4 whitespace-nowrap">Role</th>
                <th className="px-6 py-4 whitespace-nowrap text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-slate-500 text-sm">
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.user_id} className="border-b border-slate-200 hover:bg-slate-50 transition">
                    <td className="px-6 py-4 font-medium text-slate-800">{user.user_id}</td>
                    <td className="px-6 py-4 text-slate-700">{user.username}</td>
                    <td className="px-6 py-4 text-slate-600 text-xs">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                        user.role === 'admin'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDeleteUser(user.user_id, user.username)}
                        disabled={user.user_id === 1 || user.role === 'admin'}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                          user.user_id === 1 || user.role === 'admin'
                            ? 'text-slate-400 cursor-not-allowed'
                            : 'text-red-600 hover:text-red-700 border border-red-300 hover:bg-red-50'
                        }`}
                        title={
                          user.user_id === 1 
                            ? 'Cannot delete system user' 
                            : user.role === 'admin'
                            ? 'Cannot delete admin users'
                            : 'Delete user'
                        }
                      >
                        🗑️ Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
