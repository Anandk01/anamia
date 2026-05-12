/**
 * DoctorDashboard.jsx
 * Sidebar nav: New Assessment, Patient Records, Hb Trends, Alerts.
 * Alert count badge on Alerts nav item.
 */

import { useState, useEffect } from 'react';
import { FlaskConical, Users, TrendingUp, Bell, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';
import CBCForm from '../components/CBCForm.jsx';
import PredictionResult from '../components/PredictionResult.jsx';
import DietRecommendations from '../components/DietRecommendations.jsx';
import HealthTips from '../components/HealthTips.jsx';
import ReportHistory from '../components/ReportHistory.jsx';
import HbTrendChart from '../components/HbTrendChart.jsx';
import PDFDownloadButton from '../components/PDFDownloadButton.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'doctor';

  const [view, setView] = useState('assessment');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [patientUsername, setPatientUsername] = useState('');
  const [trendUsername, setTrendUsername] = useState('');
  const [alerts, setAlerts] = useState([]);
  const [alertCount, setAlertCount] = useState(0);
  const [alertsLoading, setAlertsLoading] = useState(false);

  // Fetch alert count on mount
  useEffect(() => {
    client.get('/api/alerts')
      .then((res) => {
        const data = res.data?.alerts || res.data?.records || [];
        setAlerts(data);
        setAlertCount(data.filter((a) => !a.read).length || data.length);
      })
      .catch(() => {});
  }, []);

  async function handleCBCSubmit(cbcData) {
    const target = patientUsername.trim() || username;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await client.post('/api/predict', { username: target, ...cbcData });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Prediction failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  async function markAlertRead(alertId) {
    try {
      await client.patch(`/api/alerts/${alertId}/read`);
      setAlerts((prev) => prev.map((a) => a.alert_id === alertId ? { ...a, read: true } : a));
      setAlertCount((c) => Math.max(0, c - 1));
    } catch {
      // silently fail
    }
  }

  const initials = username.slice(0, 2).toUpperCase();

  const NAV_ITEMS = [
    { id: 'assessment', label: 'New Assessment', Icon: FlaskConical },
    { id: 'records',    label: 'Patient Records', Icon: Users },
    { id: 'trends',     label: 'Hb Trends',       Icon: TrendingUp },
    { id: 'alerts',     label: 'Alerts',           Icon: Bell, badge: alertCount },
  ];

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
          {NAV_ITEMS.map(({ id, label, Icon, badge }) => (
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
              <span className="flex-1 text-left">{label}</span>
              {badge > 0 && (
                <span className="text-xs font-bold px-1.5 py-0.5 rounded-full text-white" style={{ backgroundColor: '#ef4444', minWidth: '18px', textAlign: 'center' }}>
                  {badge}
                </span>
              )}
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
              <p className="text-white text-xs font-medium truncate">Dr. {username}</p>
              <p className="text-slate-500 text-xs">Doctor</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-300 transition" title="Logout">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#f8f9fa' }}>
        <div className="h-12 bg-white border-b border-slate-200 flex items-center px-6 flex-shrink-0">
          <h2 className="text-sm font-semibold text-slate-700">
            {view === 'assessment' && 'New Assessment'}
            {view === 'records' && 'Patient Records'}
            {view === 'trends' && 'Hb Trends'}
            {view === 'alerts' && 'Critical Alerts'}
          </h2>
        </div>

        <div className="flex-1 overflow-hidden">
          {/* New Assessment */}
          {view === 'assessment' && (
            <div className="h-full flex gap-0 overflow-hidden">
              <div className="flex-shrink-0 overflow-y-auto p-5 border-r border-slate-200 bg-white" style={{ width: '420px' }}>
                <div className="mb-4">
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                    Patient Username
                  </label>
                  <input
                    type="text"
                    value={patientUsername}
                    onChange={(e) => setPatientUsername(e.target.value)}
                    placeholder="Enter patient username"
                    className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                  />
                </div>
                <CBCForm onSubmit={handleCBCSubmit} loading={loading} />
                {error && <div className="mt-3 bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
              </div>
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {loading && (
                  <div className="space-y-3 animate-pulse">
                    <div className="h-16 bg-slate-200 rounded" />
                    <div className="h-8 bg-slate-200 rounded w-3/4" />
                    <div className="h-32 bg-slate-200 rounded" />
                  </div>
                )}
                {!loading && result && (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Prediction Result</h3>
                      <PDFDownloadButton reportData={result} username={patientUsername || username} />
                    </div>
                    <PredictionResult result={result} />
                    {Array.isArray(result.diet_recs) && result.diet_recs.length > 0 && (
                      <DietRecommendations items={result.diet_recs} veganOnly={false} />
                    )}
                    {Array.isArray(result.health_tips) && result.health_tips.length > 0 && (
                      <HealthTips tips={result.health_tips} severity={result.severity_level} />
                    )}
                  </>
                )}
                {!loading && !result && (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-3">
                    <FlaskConical size={32} className="opacity-30" />
                    <p>Enter patient CBC values to run assessment</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Patient Records */}
          {view === 'records' && (
            <div className="h-full overflow-y-auto p-5">
              <ReportHistory username={username} role="doctor" />
            </div>
          )}

          {/* Hb Trends */}
          {view === 'trends' && (
            <div className="h-full overflow-y-auto p-5 space-y-4">
              <div className="bg-white rounded border border-slate-200 p-4">
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                  Patient Username
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={trendUsername}
                    onChange={(e) => setTrendUsername(e.target.value)}
                    placeholder="Enter username to view trend"
                    className="flex-1 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                  />
                </div>
              </div>
              {trendUsername && <HbTrendChart username={trendUsername} />}
            </div>
          )}

          {/* Alerts */}
          {view === 'alerts' && (
            <div className="h-full overflow-y-auto p-5">
              <div className="bg-white rounded border border-slate-200 overflow-hidden">
                <div className="px-4 py-2.5 border-b border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Critical Alerts</span>
                </div>
                {alertsLoading && (
                  <div className="flex items-center justify-center py-10 text-slate-400 text-sm">Loading...</div>
                )}
                {!alertsLoading && alerts.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-sm gap-2">
                    <Bell size={24} className="opacity-30" />
                    <p>No alerts</p>
                  </div>
                )}
                {alerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className={`flex items-start gap-3 px-4 py-3 border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition border-l-4 ${
                      !alert.read ? 'border-l-red-500' : 'border-l-transparent'
                    }`}
                    onClick={() => markAlertRead(alert.alert_id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-700">
                        Patient: {alert.patient_username}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        HGB: {alert.hgb_value} g/dL · Severity: {alert.severity_level}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">{alert.sent_at}</p>
                    </div>
                    {!alert.read && (
                      <span className="text-xs text-red-600 font-semibold flex-shrink-0">Unread</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
