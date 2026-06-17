import React, { useState, useEffect } from 'react';
import { Users, Brain, TrendingUp, Calendar } from 'lucide-react';
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import client from '../api/client';

const SEVERITY_COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444'];
const TYPE_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#14b8a6', '#f59e0b'];

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 px-4 py-3 flex items-center gap-3">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <p className="text-xl font-bold text-slate-800">{value ?? '—'}</p>
      </div>
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [range, setRange] = useState('30d');
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);

  useEffect(() => {
    client.get('/api/analytics/overview', { params: { range } })
      .then(res => setOverview(res.data))
      .catch(() => {});
    client.get('/api/analytics/trends', { params: { period_days: range === '7d' ? 7 : range === '90d' ? 90 : 30 } })
      .then(res => setTrends(res.data?.trends || res.data?.daily || []))
      .catch(() => {});
  }, [range]);

  const severityData = overview?.severity_distribution
    ? Object.entries(overview.severity_distribution).map(([name, value]) => ({ name, value }))
    : [];
  const typeData = overview?.type_distribution
    ? Object.entries(overview.type_distribution).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="space-y-5">
      {/* Date range selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Analytics Overview</h2>
        <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
          {['7d', '30d', '90d'].map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                range === r ? 'bg-indigo-500 text-white' : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={Users} label="Total Patients" value={overview?.total_patients} color="#6366f1" />
        <StatCard icon={Brain} label="Predictions" value={overview?.total_predictions} color="#8b5cf6" />
        {/* <StatCard icon={TrendingUp} label="Avg Adherence" value={overview?.avg_adherence ? `${overview.avg_adherence}%` : '—'} color="#10b981" /> */}
        <StatCard icon={Calendar} label="Appointments" value={overview?.total_appointments} color="#f59e0b" />
      </div>

      {/* Area chart */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Predictions per Day</p>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
            <Tooltip />
            <Area type="monotone" dataKey="count" stroke="#6366f1" fill="#e0e7ff" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Pie charts */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Severity Distribution</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={severityData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                {severityData.map((_, idx) => (
                  <Cell key={idx} fill={SEVERITY_COLORS[idx % SEVERITY_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Anemia Type Distribution</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                {typeData.map((_, idx) => (
                  <Cell key={idx} fill={TYPE_COLORS[idx % TYPE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
