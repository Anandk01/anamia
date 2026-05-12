/**
 * HbTrendChart.jsx
 * Recharts ComposedChart with HGB trend line, severity-colored dots,
 * and 3 reference lines at 11.9, 9.9, 8.0.
 */

import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Dot,
} from 'recharts';
import client from '../api/client.js';

const SEVERITY_DOT_COLORS = {
  None:     '#10b981',
  Mild:     '#f59e0b',
  Moderate: '#f97316',
  Severe:   '#ef4444',
};

function CustomDot(props) {
  const { cx, cy, payload } = props;
  const color = SEVERITY_DOT_COLORS[payload?.severity_level] || '#6366f1';
  return <circle cx={cx} cy={cy} r={5} fill={color} stroke="#fff" strokeWidth={2} />;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-white border border-slate-200 rounded shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-slate-700 mb-1">{d?.date?.slice(0, 10)}</p>
      <p className="text-slate-600">HGB: <strong>{d?.hgb} g/dL</strong></p>
      <p className="text-slate-500">Severity: {d?.severity_level}</p>
    </div>
  );
}

export default function HbTrendChart({ username }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    setError(null);
    client
      .get(`/api/trend/${username}`)
      .then((res) => setData(res.data.trend || []))
      .catch((err) => {
        if (err.response?.status === 404) setData([]);
        else setError(err.response?.data?.message || 'Failed to load trend data.');
      })
      .finally(() => setLoading(false));
  }, [username]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm gap-2">
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        Loading trend...
      </div>
    );
  }

  if (error) {
    return <div className="px-4 py-3 text-sm text-red-600 bg-red-50 rounded border border-red-200">{error}</div>;
  }

  if (data.length < 2) {
    return (
      <div
        className="flex flex-col items-center justify-center h-48 rounded text-slate-400 text-sm gap-2"
        style={{ border: '2px dashed #e2e8f0' }}
      >
        <span className="text-2xl">📈</span>
        <p>Submit 2+ tests to see trend</p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    date: d.date?.slice(0, 10),
  }));

  return (
    <div className="bg-white rounded border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">HGB Trend</span>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 inline-block" style={{ backgroundColor: '#f59e0b' }} /> Mild (11.9)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 inline-block" style={{ backgroundColor: '#f97316' }} /> Moderate (9.9)</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 inline-block" style={{ backgroundColor: '#ef4444' }} /> Severe (8.0)</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={11.9} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '11.9', position: 'right', fontSize: 9, fill: '#f59e0b' }} />
          <ReferenceLine y={9.9} stroke="#f97316" strokeDasharray="4 2" label={{ value: '9.9', position: 'right', fontSize: 9, fill: '#f97316' }} />
          <ReferenceLine y={8.0} stroke="#ef4444" strokeDasharray="4 2" label={{ value: '8.0', position: 'right', fontSize: 9, fill: '#ef4444' }} />
          <Line
            type="monotone"
            dataKey="hgb"
            stroke="#6366f1"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 7 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
