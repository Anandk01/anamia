/**
 * DoctorDashboard.jsx
 * Full-featured doctor dashboard with 12 nav items, stat pills, and rich home view.
 */

import { useState, useEffect } from 'react';
import {
  Home, FlaskConical, Users, Calendar, FileText, MessageCircle,
  MessageSquare, BookOpen, BarChart3, Bell, TrendingUp, Settings, LogOut,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.js';
import { useSocket } from '../contexts/SocketContext.jsx';
import client from '../api/client.js';

import CBCForm from '../components/CBCForm.jsx';
import PredictionResult from '../components/PredictionResult.jsx';
import DietRecommendations from '../components/DietRecommendations.jsx';
import HealthTips from '../components/HealthTips.jsx';
import ReportHistory from '../components/ReportHistory.jsx';
import HbTrendChart from '../components/HbTrendChart.jsx';
import PDFDownloadButton from '../components/PDFDownloadButton.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';
import DoctorSchedule from '../components/DoctorSchedule.jsx';
import DoctorChat from '../components/DoctorChat.jsx';
import Forum from '../components/Forum.jsx';
import PostDetail from '../components/PostDetail.jsx';
import CreatePost from '../components/CreatePost.jsx';
import ArticleEditor from '../components/ArticleEditor.jsx';
import PrescriptionForm from '../components/PrescriptionForm.jsx';
import AnalyticsDashboard from '../components/AnalyticsDashboard.jsx';
import DoctorAvailability from '../components/DoctorAvailability.jsx';
import PrescribeMedicationForm from '../components/PrescribeMedicationForm.jsx';
import ProfileSettings from '../components/ProfileSettings.jsx';
import NotificationBell from '../components/NotificationBell.jsx';
import ThemeToggle from '../components/ThemeToggle.jsx';
import Breadcrumb from '../components/Breadcrumb.jsx';
import StatusFooter from '../components/StatusFooter.jsx';

function StatPill({ label, value, color }) {
  return (
    <div className="flex items-center gap-2 bg-white rounded-lg border border-slate-200 px-3 py-1.5">
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-bold text-slate-700">{value ?? '—'}</span>
    </div>
  );
}

function StatCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 flex items-center gap-3 shadow-md hover:scale-[1.02] transition-transform">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-lg font-bold text-slate-800 dark:text-white">{value ?? '—'}</p>
        {sub && <p className="text-xs text-slate-400">{sub}</p>}
      </div>
    </div>
  );
}

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'doctor';

  const [view, setView] = useState('home');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [patientUsername, setPatientUsername] = useState('');
  const [assignedPatients, setAssignedPatients] = useState([]);
  const [trendUsername, setTrendUsername] = useState('');
  const [badges, setBadges] = useState({});
  const [quickStats, setQuickStats] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [showPrescribeModal, setShowPrescribeModal] = useState(false);

  // Real-time badge counts from global socket
  const { unreadMessages, pendingAppointments, activeAlerts } = useSocket() || {};

  // Forum state
  const [forumView, setForumView] = useState('list');
  const [selectedPost, setSelectedPost] = useState(null);

  useEffect(() => {
    client.get('/api/alerts/mine').then(r => {
      const data = r.data?.alerts || r.data?.records || [];
      setAlerts(data);
      setBadges(b => ({ ...b, alerts: data.filter(a => !a.read).length }));
    }).catch(() => {});
    client.get('/api/notifications/unread-count').then(r => setBadges(b => ({ ...b, messages: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/appointments/pending-count').then(r => setBadges(b => ({ ...b, appointments: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/analytics/overview').then(r => setQuickStats(r.data || {})).catch(() => {});
    // Fetch assigned patients for CBC form dropdown
    client.get('/api/assignment/my-patients').then(r => {
      setAssignedPatients(r.data?.patients || []);
    }).catch(() => setAssignedPatients([]));
  }, []);

  const NAV_ITEMS = [
    { id: 'home', label: 'Home', Icon: Home },
    { id: 'assessment', label: 'New Assessment', Icon: FlaskConical },
    { id: 'records', label: 'Patient Records', Icon: Users },
    { id: 'schedule', label: 'Appointments', Icon: Calendar, badge: pendingAppointments || badges.appointments, badgeColor: '#3b82f6' },
    { id: 'prescribe', label: 'Prescribe', Icon: FileText },
    { id: 'messages', label: 'Messages', Icon: MessageCircle, badge: unreadMessages || badges.messages },
    { id: 'forum', label: 'Forum', Icon: MessageSquare },
    { id: 'articles', label: 'Articles', Icon: BookOpen },
    { id: 'analytics', label: 'Analytics', Icon: BarChart3 },
    { id: 'alerts', label: 'Alerts', Icon: Bell, badge: activeAlerts || badges.alerts, badgeColor: '#ef4444' },
    { id: 'trends', label: 'Hb Trends', Icon: TrendingUp },
    { id: 'settings', label: 'Settings', Icon: Settings },
  ];

  async function handleCBCSubmit(cbcData) {
    const target = patientUsername.trim() || username;
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await client.post('/api/predict', { username: target, ...cbcData });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Prediction failed.');
    } finally { setLoading(false); }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  async function markAlertRead(alertId) {
    try {
      await client.patch(`/api/alerts/${alertId}/read`);
      setAlerts(prev => prev.map(a => a.alert_id === alertId ? { ...a, read: true } : a));
      setBadges(b => ({ ...b, alerts: Math.max(0, (b.alerts || 0) - 1) }));
    } catch {}
  }

  const initials = username.slice(0, 2).toUpperCase();
  const activeLabel = NAV_ITEMS.find(n => n.id === view)?.label || 'Dashboard';

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Sidebar */}
      <div className="flex flex-col flex-shrink-0 rounded-r-xl" style={{ width: '220px', backgroundColor: '#0f1117' }}>
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
              onClick={() => { setView(id); if (id !== 'forum') { setForumView('list'); setSelectedPost(null); } }}
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
              <p className="text-white text-xs font-medium truncate">Dr. {username}</p>
              <p className="text-slate-500 text-[10px]">Doctor</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-300" title="Logout"><LogOut size={14} /></button>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
        {/* Header */}
        <div className="h-12 bg-gradient-to-r from-indigo-500 to-purple-600 border-b border-slate-200 flex items-center justify-between px-5 flex-shrink-0">
          <Breadcrumb items={['Dashboard', activeLabel]} />
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <NotificationBell />
            {badges.appointments > 0 && (
              <span className="text-xs bg-amber-100 text-amber-700 font-medium px-2 py-0.5 rounded-full">{badges.appointments} pending</span>
            )}
          </div>
        </div>

        {/* Quick stats */}
        <div className="flex items-center gap-3 px-5 py-2 bg-white border-b border-slate-100 flex-shrink-0">
          <StatPill label="Patients" value={quickStats.total_users || '—'} color="#6366f1" />
          <StatPill label="Pending Appts" value={badges.appointments || 0} color="#f59e0b" />
          <StatPill label="Critical Alerts" value={badges.alerts || 0} color="#ef4444" />
          <StatPill label="Avg Adherence" value={quickStats.avg_adherence ? `${quickStats.avg_adherence}%` : '—'} color="#10b981" />
        </div>

        {/* Content */}
        <div id="main-content" className="flex-1 overflow-y-auto p-5">
          {/* Home */}
          {view === 'home' && (
            <div className="space-y-5">
              <div className="grid grid-cols-3 gap-4">
                <StatCard label="Total Patients" value={quickStats.total_users} icon={Users} color="#6366f1" />
                <StatCard label="Predictions Today" value={quickStats.predictions_today || quickStats.total_predictions} icon={FlaskConical} color="#8b5cf6" />
                <StatCard label="Critical Alerts" value={badges.alerts || 0} icon={Bell} color="#ef4444" />
                <StatCard label="Pending Appointments" value={badges.appointments || 0} icon={Calendar} color="#f59e0b" />
                <StatCard label="Severe Cases" value={quickStats.severe_cases || 0} icon={TrendingUp} color="#ef4444" sub="HGB < 8.0" />
                <StatCard label="Avg Adherence" value={quickStats.avg_adherence ? `${quickStats.avg_adherence}%` : '—'} icon={BarChart3} color="#10b981" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Today's Schedule */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Today's Schedule</p>
                  <DoctorSchedule compact />
                </div>
                {/* Critical Alerts */}
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Critical Alerts</p>
                  {alerts.filter(a => !a.read).slice(0, 4).map(alert => (
                    <div key={alert.alert_id} className="flex items-center gap-2 py-2 border-b border-slate-50 last:border-0">
                      <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-700 truncate">{alert.patient_username} — HGB: {alert.hgb_value}</p>
                        <p className="text-xs text-slate-400">{alert.severity_level}</p>
                      </div>
                    </div>
                  ))}
                  {alerts.filter(a => !a.read).length === 0 && <p className="text-sm text-slate-400">No critical alerts</p>}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-4 gap-3">
                <button onClick={() => setView('assessment')} className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl p-3 text-xs font-medium hover:scale-[1.02] transition-transform shadow-lg flex items-center gap-2">
                  <FlaskConical size={14} /> New Assessment
                </button>
                <button onClick={() => setView('prescribe')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-xs font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-transform shadow-md flex items-center gap-2">
                  <FileText size={14} /> Prescribe
                </button>
                <button onClick={() => setView('schedule')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-xs font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-transform shadow-md flex items-center gap-2">
                  <Calendar size={14} /> Appointments
                </button>
                <button onClick={() => setView('records')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-xs font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-transform shadow-md flex items-center gap-2">
                  <Users size={14} /> Records
                </button>
              </div>
            </div>
          )}

          {/* Assessment */}
          {view === 'assessment' && (
            <div className="flex gap-5">
              <div className="w-[420px] flex-shrink-0 bg-white rounded-lg border border-slate-200 p-4">
                <div className="mb-4">
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Select Patient</label>
                  <select
                    value={patientUsername}
                    onChange={e => setPatientUsername(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select patient...</option>
                    {assignedPatients.map(p => (
                      <option key={p.username || p} value={p.username || p}>{p.username || p}</option>
                    ))}
                  </select>
                </div>
                <CBCForm onSubmit={handleCBCSubmit} loading={loading} />
                {error && <div className="mt-3 bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
              </div>
              <div className="flex-1 space-y-4">
                {loading && <div className="animate-pulse space-y-3"><div className="h-16 bg-slate-200 rounded" /><div className="h-32 bg-slate-200 rounded" /></div>}
                {!loading && result && (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase">Result</h3>
                      <div className="flex gap-2">
                        <PDFDownloadButton reportData={result} username={patientUsername || username} />
                        <button
                          onClick={() => setShowPrescribeModal(true)}
                          className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700"
                        >
                          + Prescribe Medication
                        </button>
                      </div>
                    </div>
                    <PredictionResult result={result} />
                    {Array.isArray(result.diet_recs) && result.diet_recs.length > 0 && <DietRecommendations items={result.diet_recs} veganOnly={false} />}
                    {Array.isArray(result.health_tips) && result.health_tips.length > 0 && <HealthTips tips={result.health_tips} severity={result.severity_level} />}
                  </>
                )}
                {!loading && !result && (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-sm gap-3">
                    <FlaskConical size={32} className="opacity-30" />
                    <p>Enter patient CBC values to run assessment</p>
                  </div>
                )}
              </div>

              {/* Prescribe Medication Modal */}
              {showPrescribeModal && patientUsername && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-white rounded-xl p-6 w-[480px] max-h-[80vh] overflow-y-auto shadow-2xl">
                    <h3 className="text-lg font-semibold mb-4">Prescribe Medication</h3>
                    <PrescribeMedicationForm
                      patientUsername={patientUsername}
                      predictionId={result?.prediction_id}
                      onClose={() => setShowPrescribeModal(false)}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {view === 'records' && <ReportHistory username={username} role="doctor" />}
          {view === 'schedule' && <DoctorSchedule />}
          {view === 'prescribe' && <PrescriptionForm />}
          {view === 'messages' && <DoctorChat />}
          {view === 'forum' && (
            <div className="transition-all duration-200">
              {forumView === 'list' && (
                <Forum
                  onSelectPost={(post) => { setSelectedPost(post); setForumView('detail'); }}
                  onNewPost={() => setForumView('create')}
                />
              )}
              {forumView === 'detail' && selectedPost && (
                <PostDetail
                  postId={selectedPost.id}
                  onBack={() => { setForumView('list'); setSelectedPost(null); }}
                />
              )}
              {forumView === 'create' && (
                <CreatePost
                  onBack={() => setForumView('list')}
                  onCreated={() => setForumView('list')}
                />
              )}
            </div>
          )}
          {view === 'articles' && <ArticleEditor />}
          {view === 'analytics' && <AnalyticsDashboard />}
          {view === 'alerts' && (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <span className="text-xs font-semibold text-slate-500 uppercase">Critical Alerts</span>
              </div>
              {alerts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-sm gap-2">
                  <Bell size={24} className="opacity-30" /><p>No alerts</p>
                </div>
              )}
              {alerts.map(alert => (
                <div
                  key={alert.alert_id}
                  className={`flex items-start gap-3 px-4 py-3 border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition border-l-4 ${!alert.read ? 'border-l-red-500' : 'border-l-transparent'}`}
                  onClick={() => markAlertRead(alert.alert_id)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-700">Patient: {alert.patient_username}</p>
                    <p className="text-xs text-slate-500 mt-0.5">HGB: {alert.hgb_value} g/dL · Severity: {alert.severity_level}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{alert.sent_at}</p>
                  </div>
                  {!alert.read && <span className="text-xs text-red-600 font-semibold">Unread</span>}
                </div>
              ))}
            </div>
          )}
          {view === 'trends' && (
            <div className="space-y-4">
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Patient Username</label>
                <input type="text" value={trendUsername} onChange={e => setTrendUsername(e.target.value)} placeholder="Enter username to view trend" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              {trendUsername && <HbTrendChart username={trendUsername} />}
            </div>
          )}
          {view === 'settings' && (
            <div className="space-y-6">
              <DoctorAvailability />
              <ProfileSettings />
            </div>
          )}
        </div>

        <StatusFooter />
      </div>
    </div>
  );
}
