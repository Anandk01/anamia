/**
 * PatientDashboard.jsx
 * Fixed layout: 220px dark sidebar + content area.
 * Views: New Test, History, Progress, Chat.
 */

import { useState } from 'react';
import { FlaskConical, Table2, TrendingUp, MessageCircle, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';
import CBCForm from '../components/CBCForm.jsx';
import PredictionResult from '../components/PredictionResult.jsx';
import DietRecommendations from '../components/DietRecommendations.jsx';
import HealthTips from '../components/HealthTips.jsx';
import ReportHistory from '../components/ReportHistory.jsx';
import HbTrendChart from '../components/HbTrendChart.jsx';
import PDFDownloadButton from '../components/PDFDownloadButton.jsx';
import Chatbot from '../components/Chatbot.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-16 bg-slate-200 rounded" />
      <div className="h-8 bg-slate-200 rounded w-3/4" />
      <div className="h-8 bg-slate-200 rounded w-1/2" />
      <div className="h-32 bg-slate-200 rounded" />
    </div>
  );
}

export default function PatientDashboard() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'patient';

  const [view, setView] = useState('test');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [veganOnly, setVeganOnly] = useState(user?.vegan_diet === 1);

  const NAV_ITEMS = [
    { id: 'test',     label: t('new_test'),  Icon: FlaskConical },
    { id: 'history',  label: t('history'),   Icon: Table2 },
    { id: 'progress', label: t('progress'),  Icon: TrendingUp },
    { id: 'chat',     label: t('chat'),      Icon: MessageCircle },
  ];
  async function handleCBCSubmit(cbcData) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await client.post('/api/predict', { username, ...cbcData });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Prediction failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  // Initials avatar
  const initials = username.slice(0, 2).toUpperCase();

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* ── Sidebar ── */}
      <div
        className="flex flex-col flex-shrink-0"
        style={{ width: '220px', backgroundColor: '#0f1117' }}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded flex items-center justify-center text-white font-bold text-xs" style={{ backgroundColor: '#6366f1' }}>A</div>
            <span className="text-white font-semibold text-sm tracking-tight">AnemiaDetect</span>
          </div>
        </div>

        {/* Nav */}
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

        {/* Footer */}
        <div className="px-3 py-4 border-t border-slate-800 space-y-3">
          <LanguageSelector />
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ backgroundColor: '#6366f1' }}>
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">{username}</p>
              <p className="text-slate-500 text-xs">Patient</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-300 transition" title="Logout">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#f8f9fa' }}>
        {/* Header */}
        <div className="h-12 bg-white border-b border-slate-200 flex items-center px-6 flex-shrink-0">
          <h2 className="text-sm font-semibold text-slate-700">
            {view === 'test' && t('new_test')}
            {view === 'history' && t('history')}
            {view === 'progress' && t('progress')}
            {view === 'chat' && t('chat')}
          </h2>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          {/* ── New Test view ── */}
          {view === 'test' && (
            <div className="h-full flex gap-0 overflow-hidden">
              {/* Left: CBC Form (fixed 400px) */}
              <div className="flex-shrink-0 overflow-y-auto p-5 border-r border-slate-200 bg-white" style={{ width: '400px' }}>
                <CBCForm onSubmit={handleCBCSubmit} loading={loading} />
                {error && (
                  <div className="mt-3 bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>
                )}
              </div>

              {/* Right: Result area */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {loading && <Skeleton />}
                {!loading && result && (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t('prediction_result') || 'Prediction Result'}</h3>
                      <PDFDownloadButton reportData={result} username={username} />
                    </div>
                    <PredictionResult result={result} />
                    {Array.isArray(result.diet_recs) && result.diet_recs.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={veganOnly}
                              onChange={(e) => setVeganOnly(e.target.checked)}
                              className="rounded"
                            />
                            {t('vegan_filter')}
                          </label>
                        </div>
                        <DietRecommendations items={result.diet_recs} veganOnly={veganOnly} />
                      </div>
                    )}
                    {Array.isArray(result.health_tips) && result.health_tips.length > 0 && (
                      <HealthTips tips={result.health_tips} severity={result.severity_level} />
                    )}
                  </>
                )}
                {!loading && !result && (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-3">
                    <FlaskConical size={32} className="opacity-30" />
                    <p>Enter CBC values and submit to see prediction</p>                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── History view ── */}
          {view === 'history' && (
            <div className="h-full overflow-y-auto p-5">
              <ReportHistory username={username} role="patient" />
            </div>
          )}

          {/* ── Progress view ── */}
          {view === 'progress' && (
            <div className="h-full overflow-y-auto p-5">
              <HbTrendChart username={username} />
            </div>
          )}

          {/* ── Chat view ── */}
          {view === 'chat' && (
            <div className="h-full flex items-center justify-center text-slate-400 text-sm">
              <div className="text-center space-y-2">
                <MessageCircle size={32} className="mx-auto opacity-30" />
                <p>Use the chat button in the bottom-right corner</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Floating chatbot */}
      <Chatbot />
    </div>
  );
}
