import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';

function getBarColor(percent) {
  if (percent > 80) return '#22c55e';
  if (percent >= 50) return '#eab308';
  return '#ef4444';
}

export default function AdherenceChart({ data = [] }) {
  const [range, setRange] = useState(7);

  const displayData = data.slice(-range);

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg">Medication Adherence</h3>
        <div className="flex gap-1">
          <button
            onClick={() => setRange(7)}
            className={`px-3 py-1 text-sm rounded ${range === 7 ? 'bg-indigo-600 text-white' : 'bg-slate-100'}`}
          >
            7 days
          </button>
          <button
            onClick={() => setRange(30)}
            className={`px-3 py-1 text-sm rounded ${range === 30 ? 'bg-indigo-600 text-white' : 'bg-slate-100'}`}
          >
            30 days
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={displayData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value) => [`${value}%`, 'Adherence']}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <ReferenceLine y={80} stroke="#6366f1" strokeDasharray="4 4" label="Target" />
          {/* <Bar dataKey="adherence_percent" radius={[4, 4, 0, 0]}>
            {displayData.map((entry, idx) => (
              <Cell key={idx} fill={getBarColor(entry.adherence_percent)} />
            ))}
          </Bar> */}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
