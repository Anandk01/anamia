/**
 * PatientDashboard.jsx
 * Full-featured patient dashboard with 13 nav items, stat pills, and rich home view.
 */

import { useState, useEffect } from 'react';
import {
  Home, FlaskConical, Table2, TrendingUp, Calendar, Pill, MessageCircle,
  MessageSquare, BookOpen, FileText, Utensils, Stethoscope, Settings, LogOut,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
import Chatbot from '../components/Chatbot.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';
import AppointmentCalendar from '../components/AppointmentCalendar.jsx';
import BookingModal from '../components/BookingModal.jsx';
import MedicationTracker from '../components/MedicationTracker.jsx';
import DoctorChat from '../components/DoctorChat.jsx';
import Forum from '../components/Forum.jsx';
import PostDetail from '../components/PostDetail.jsx';
import CreatePost from '../components/CreatePost.jsx';
import EducationCenter from '../components/EducationCenter.jsx';
import PrescriptionView from '../components/PrescriptionView.jsx';
import SymptomChecker from '../components/SymptomChecker.jsx';
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

export default function PatientDashboard() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { logout, getUser } = useAuth();
  const user = getUser();
  const username = user?.username || 'patient';

  const [view, setView] = useState('home');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [veganOnly, setVeganOnly] = useState(user?.vegan_diet === 1);
  const [badges, setBadges] = useState({});
  const [quickStats, setQuickStats] = useState({});

  // Real-time badge counts from global socket
  const { unreadMessages, pendingAppointments, activeAlerts } = useSocket() || {};

  // Booking modal state
  const [showBooking, setShowBooking] = useState(false);
  const [bookingSlot, setBookingSlot] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [assignedDoctor, setAssignedDoctor] = useState(null);
  const [doctorCheckDone, setDoctorCheckDone] = useState(false);

  // Forum state
  const [forumView, setForumView] = useState('list');
  const [selectedPost, setSelectedPost] = useState(null);

  useEffect(() => {
    // Fetch badge counts
    client.get('/api/notifications/unread-count').then(r => setBadges(b => ({ ...b, messages: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/appointments/pending-count').then(r => setBadges(b => ({ ...b, appointments: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/medications/due-today').then(r => setBadges(b => ({ ...b, medications: r.data?.count || 0 }))).catch(() => {});
    // Quick stats
    client.get('/api/profile/quick-stats').then(r => setQuickStats(r.data || {})).catch(() => {});
    // Check assigned doctor
    client.get('/api/assignment/my-doctor').then(r => {
      setAssignedDoctor(r.data?.doctor || null);
      setDoctorCheckDone(true);
    }).catch(() => setDoctorCheckDone(true));
    // Fetch doctors for booking modal
    client.get('/api/appointments/doctors').then(r => {
      const list = r.data?.doctors || [];
      setDoctors(list.map(d => ({ id: d.id, name: d.name || d.username, specialization: d.specialization })));
    }).catch(() => {
      setDoctors([]);
    });
  }, []);

  const NAV_ITEMS = [
    { id: 'home', label: 'Home', Icon: Home },
    { id: 'test', label: 'New Test', Icon: FlaskConical },
    { id: 'history', label: 'History', Icon: Table2 },
    { id: 'progress', label: 'Progress', Icon: TrendingUp },
    { id: 'appointments', label: 'Appointments', Icon: Calendar, badge: pendingAppointments || badges.appointments },
    { id: 'medications', label: 'Medications', Icon: Pill, badge: badges.medications, badgeColor: '#f59e0b' },
    { id: 'messages', label: 'Messages', Icon: MessageCircle, badge: unreadMessages || badges.messages },
    { id: 'forum', label: 'Forum', Icon: MessageSquare },
    { id: 'education', label: 'Education', Icon: BookOpen },
    { id: 'prescriptions', label: 'Prescriptions', Icon: FileText },
    { id: 'diet', label: 'Diet Plan', Icon: Utensils },
    { id: 'symptom', label: 'Symptom Checker', Icon: Stethoscope },
    { id: 'settings', label: 'Settings', Icon: Settings },
  ];

  async function handleCBCSubmit(cbcData) {
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await client.post('/api/predict', { username, ...cbcData });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Prediction failed.');
    } finally { setLoading(false); }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
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
              <p className="text-white text-xs font-medium truncate">{username}</p>
              <p className="text-slate-500 text-[10px]">Patient</p>
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
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: '#6366f1' }}>{initials}</div>
          </div>
        </div>

        {/* Quick stats bar */}
        <div className="flex items-center gap-3 px-5 py-2 bg-white border-b border-slate-100 flex-shrink-0">
          <StatPill label="Next Appt" value={quickStats.next_appointment || 'None'} color="#6366f1" />
          <StatPill label="Meds Due" value={badges.medications || 0} color="#f59e0b" />
          <StatPill label="Adherence" value={quickStats.adherence ? `${quickStats.adherence}%` : '—'} color="#10b981" />
          <StatPill label="Unread" value={badges.messages || 0} color="#ef4444" />
        </div>

        {/* Content */}
        <div id="main-content" className="flex-1 overflow-y-auto p-5">
          {/* Home */}
          {view === 'home' && (
            <div className="space-y-5">
              <div className="grid grid-cols-4 gap-4">
                <StatCard label="Total Tests" value={quickStats.total_tests} icon={FlaskConical} color="#6366f1" />
                <StatCard label="Last HGB" value={quickStats.last_hgb ? `${quickStats.last_hgb} g/dL` : '—'} icon={TrendingUp} color="#10b981" />
                <StatCard label="Adherence" value={quickStats.adherence ? `${quickStats.adherence}%` : '—'} icon={Pill} color="#f59e0b" />
                <StatCard label="Appointments" value={badges.appointments || 0} icon={Calendar} color="#8b5cf6" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">HGB Trend</p>
                  <HbTrendChart username={username} compact />
                </div>
                <div className="bg-white rounded-lg border border-slate-200 p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Today's Medications</p>
                  <MedicationTracker compact />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <button onClick={() => setView('test')} className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl p-4 text-sm font-medium hover:scale-[1.02] transition-transform shadow-lg flex items-center gap-2">
                  <FlaskConical size={16} /> New Blood Test
                </button>
                <button onClick={() => setView('appointments')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 text-sm font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-transform shadow-md flex items-center gap-2">
                  <Calendar size={16} /> Book Appointment
                </button>
                <button onClick={() => setView('education')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 text-sm font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-transform shadow-md flex items-center gap-2">
                  <BookOpen size={16} /> Learn About Anemia
                </button>
              </div>
            </div>
          )}

          {/* New Test */}
          {view === 'test' && (
            <div className="flex gap-5">
              <div className="w-96 flex-shrink-0 bg-white rounded-lg border border-slate-200 p-4">
                <CBCForm onSubmit={handleCBCSubmit} loading={loading} />
                {error && <div className="mt-3 bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
              </div>
              <div className="flex-1 space-y-4">
                {loading && <div className="animate-pulse space-y-3"><div className="h-16 bg-slate-200 rounded" /><div className="h-32 bg-slate-200 rounded" /></div>}
                {!loading && result && (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase">Result</h3>
                      <PDFDownloadButton reportData={result} username={username} />
                    </div>
                    <PredictionResult result={result} />
                    {Array.isArray(result.diet_recs) && result.diet_recs.length > 0 && <DietRecommendations items={result.diet_recs} veganOnly={veganOnly} />}
                    {Array.isArray(result.health_tips) && result.health_tips.length > 0 && <HealthTips tips={result.health_tips} severity={result.severity_level} />}
                  </>
                )}
                {!loading && !result && (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-sm gap-3">
                    <FlaskConical size={32} className="opacity-30" />
                    <p>Enter CBC values and submit to see prediction</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {view === 'history' && <ReportHistory username={username} role="patient" />}
          {view === 'progress' && <HbTrendChart username={username} source="doctor" />}
          {view === 'appointments' && (
            <>
              {doctorCheckDone && !assignedDoctor ? (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500 text-sm gap-3">
                  <Calendar size={32} className="opacity-30" />
                  <p className="font-medium">You have not been assigned to a doctor yet.</p>
                  <p className="text-xs text-slate-400">Please contact admin to get assigned to a doctor before booking appointments.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-slate-800">Appointments</h2>
                    <button
                      onClick={() => setShowBooking(true)}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition"
                    >
                      + Book Appointment
                    </button>
                  </div>
                  <AppointmentCalendar
                    onSlotClick={(slot) => { setBookingSlot(slot); setShowBooking(true); }}
                  />
                  <BookingModal
                    isOpen={showBooking}
                    onClose={() => { setShowBooking(false); setBookingSlot(null); }}
                    doctors={doctors}
                  />
                </>
              )}
            </>
          )}
          {view === 'medications' && <MedicationTracker />}
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
          {view === 'education' && <EducationCenter />}
          {view === 'prescriptions' && <PrescriptionView />}
          {view === 'diet' && <DietRecommendations items={[]} veganOnly={veganOnly} />}
          {view === 'symptom' && <SymptomChecker />}
          {view === 'settings' && <ProfileSettings />}
        </div>

        <StatusFooter />
      </div>

      <Chatbot />
    </div>
  );
}
