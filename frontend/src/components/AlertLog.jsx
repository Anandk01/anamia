/**
 * AlertLog.jsx
 * Dense table with auto-refresh every 30s.
 */

import { useState, useEffect, useRef } from 'react';
import client from '../api/client.js';

const STATUS_BADGE = {
  sent:    'bg-emerald-100 text-emerald-700',
  pending: 'bg-amber-100 text-amber-700',
  failed:  'bg-red-100 text-red-700',
};

export default function AlertLog() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  async function fetchAlerts() {
    setLoading(true);
    setError(null);
    try {
      const res = await client.get('/api/alerts');
      setAlerts(res.data?.alerts || res.data?.records || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load alerts.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAlerts();
    intervalRef.current = setInterval(fetchAlerts, 30000);
    return () => clearInterval(intervalRef.current);
  }, []);

  return (
    <div className="bg-white rounded border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Alert Log</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Auto-refresh 30s</span>
          <button onClick={fetchAlerts} className="text-xs text-indigo-600 hover:text-indigo-800 transition">↻</button>
        </div>
      </div>

      {loading && alerts.length === 0 && (
        <div className="flex items-center justify-center py-8 text-slate-400 text-sm gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Loading...
        </div>
      )}

      {error && <div className="px-4 py-3 text-sm text-red-600 bg-red-50">{error}</div>}

      {!loading && !error && alerts.length === 0 && (
        <div className="flex flex-col items-center justify-center py-10 text-slate-400 text-sm gap-2">
          <span className="text-2xl">🔔</span>
          <p>No alerts recorded</p>
        </div>
      )}

      {alerts.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-3 py-2 text-left">Patient</th>
                <th className="px-3 py-2 text-left">HGB</th>
                <th className="px-3 py-2 text-left">Severity</th>
                <th className="px-3 py-2 text-left">Recipient</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Sent At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {alerts.map((a) => (
                <tr key={a.alert_id} className="hover:bg-slate-50 transition" style={{ height: '36px' }}>
                  <td className="px-3 py-1.5 font-medium text-slate-700">{a.patient_username}</td>
                  <td className="px-3 py-1.5 font-mono text-slate-600">{a.hgb_value}</td>
                  <td className="px-3 py-1.5">
                    <span className="text-xs font-semibold text-red-600">{a.severity_level}</span>
                  </td>
                  <td className="px-3 py-1.5 text-slate-500 text-xs">{a.recipient_username}</td>
                  <td className="px-3 py-1.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGE[a.delivery_status] || 'bg-slate-100 text-slate-600'}`}>
                      {a.delivery_status}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-slate-400 text-xs whitespace-nowrap">{a.sent_at?.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
