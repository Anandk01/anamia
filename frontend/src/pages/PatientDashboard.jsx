/**
 * PatientDashboard.jsx
 * Full-featured patient dashboard with 13 nav items, stat pills, and rich home view.
 */

import { useState, useEffect } from 'react';
import {
  Home, Table2, TrendingUp, Calendar, Pill,
  FileText, Utensils, Stethoscope, Settings, LogOut, FlaskConical,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth.js';
import { useSocket } from '../contexts/SocketContext.jsx';
import client from '../api/client.js';

import ReportHistory from '../components/ReportHistory.jsx';
import HbTrendChart from '../components/HbTrendChart.jsx';
import Chatbot from '../components/Chatbot.jsx';
import LanguageSelector from '../components/LanguageSelector.jsx';
import AppointmentCalendar from '../components/AppointmentCalendar.jsx';
import BookingModal from '../components/BookingModal.jsx';
import MedicationTracker from '../components/MedicationTracker.jsx';
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

function DietFromPrescriptions() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/api/prescriptions/mine')
      .then(res => setPrescriptions(res.data?.prescriptions || []))
      .catch(() => setPrescriptions([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-slate-400">Loading diet plans...</div>;

  const withDiet = prescriptions.filter(p => p.diet_plan);
  if (withDiet.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-sm gap-2" style={{ border: '2px dashed #e2e8f0', borderRadius: '0.5rem' }}>
        <span className="text-2xl">🥗</span>
        <p>No diet plans prescribed yet</p>
        <p className="text-xs">Your doctor will add diet recommendations with your prescriptions</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Diet Plans</h2>
      {withDiet.map((p, idx) => (
        <div key={idx} className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-slate-700">From Dr. {p.doctor_username || 'Unknown'}</p>
            <p className="text-xs text-slate-400">{p.prescribed_at || p.created_at || ''}</p>
          </div>
          <div className="text-sm text-slate-600 whitespace-pre-wrap">{p.diet_plan}</div>
        </div>
      ))}
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
  const [badges, setBadges] = useState({});
  const [quickStats, setQuickStats] = useState({});

  // Real-time badge counts from global socket
  const { unreadMessages, pendingAppointments, activeAlerts, addListener, removeListener } = useSocket() || {};

  // Counter to force re-render of progress view when new report arrives
  const [progressKey, setProgressKey] = useState(0);

  // Listen for new_report socket event to refresh HbTrendChart / progress view
  useEffect(() => {
    if (!addListener) return;
    const handleNewReport = () => {
      setProgressKey(prev => prev + 1);
    };
    addListener('new_report', handleNewReport);
    return () => {
      if (removeListener) removeListener('new_report', handleNewReport);
    };
  }, [addListener, removeListener]);

  // Booking modal state
  const [showBooking, setShowBooking] = useState(false);
  const [bookingSlot, setBookingSlot] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [myAppointments, setMyAppointments] = useState([]);

  useEffect(() => {
    // Fetch badge counts
    client.get('/api/notifications/unread-count').then(r => setBadges(b => ({ ...b, messages: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/appointments/pending-count').then(r => setBadges(b => ({ ...b, appointments: r.data?.count || 0 }))).catch(() => {});
    client.get('/api/medications/due-today').then(r => setBadges(b => ({ ...b, medications: r.data?.count || 0 }))).catch(() => {});
    // Quick stats
    client.get('/api/profile/quick-stats').then(r => setQuickStats(r.data || {})).catch(() => {});
    // Fetch doctors for booking modal
    client.get('/api/appointments/doctors').then(r => {
      const list = r.data?.doctors || [];
      setDoctors(list.map(d => ({ id: d.id, name: d.name || d.username, specialization: d.specialization })));
    }).catch(() => {
      setDoctors([]);
    });
    // Fetch appointments for cancel list
    fetchMyAppointments();
  }, []);

  function getThisMonday() {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    return d.toISOString().split('T')[0];
  }

  const fetchMyAppointments = () => {
    client.get('/api/appointments/calendar?week_start=' + getThisMonday())
      .then(r => setMyAppointments(r.data?.appointments || []))
      .catch(() => {});
  };

  const cancelMyAppointment = async (appointmentId) => {
    const reason = prompt("Reason for cancellation:");
    if (!reason) return;
    try {
      await client.put(`/api/appointments/${appointmentId}/cancel`, { reason });
      setMyAppointments(prev => prev.map(a =>
        (a.appointment_id || a.id) === appointmentId ? { ...a, status: 'cancelled' } : a
      ));
    } catch {}
  };

  const NAV_ITEMS = [
    { id: 'home', label: 'Home', Icon: Home },
    { id: 'history', label: 'History', Icon: Table2 },
    { id: 'appointments', label: 'Appointments', Icon: Calendar, badge: pendingAppointments || badges.appointments },
    { id: 'medications', label: 'Medications', Icon: Pill, badge: badges.medications, badgeColor: '#f59e0b' },
    { id: 'prescriptions', label: 'Prescriptions', Icon: FileText },
    { id: 'diet', label: 'Diet Plan', Icon: Utensils },
    { id: 'symptom', label: 'Symptom Checker', Icon: Stethoscope },
    { id: 'settings', label: 'Settings', Icon: Settings },
  ];

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const initials = username.slice(0, 2).toUpperCase();
  const activeLabel = NAV_ITEMS.find(n => n.id === view)?.label || 'Dashboard';

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Sidebar */}
      <div className="flex flex-col flex-shrink-0" style={{ width: '220px', backgroundColor: '#0f1117' }}>
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
              onClick={() => {
                setView(id);
                // Clear badge when section is viewed
                if (id === 'appointments') setBadges(b => ({ ...b, appointments: 0 }));
                if (id === 'medications') setBadges(b => ({ ...b, medications: 0 }));
              }}
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
        <div className="h-12 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-5 flex-shrink-0">
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
            <div className="space-y-5 animate-slide-up">
              {/* Welcome banner */}
              <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-2xl p-6 text-white shadow-xl">
                <h2 className="text-2xl font-bold">Welcome back, {username}! 👋</h2>
                <p className="text-indigo-100 mt-1 text-sm">Your health dashboard at a glance</p>
                {quickStats.last_hgb && (
                  <div className="mt-3 inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: quickStats.last_hgb >= 12 ? '#10b981' : quickStats.last_hgb >= 10 ? '#f59e0b' : '#ef4444' }} />
                    <span className="text-sm font-medium">
                      HGB: {quickStats.last_hgb} g/dL — {quickStats.last_hgb >= 12 ? 'Normal' : quickStats.last_hgb >= 10 ? 'Mild Anemia' : 'Needs Attention'}
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="animate-slide-up animate-slide-up-delay-1">
                  <StatCard label="Total Tests" value={quickStats.total_tests} icon={FlaskConical} color="#6366f1" />
                </div>
                <div className="animate-slide-up animate-slide-up-delay-2">
                  <StatCard label="Last HGB" value={quickStats.last_hgb ? `${quickStats.last_hgb} g/dL` : '—'} icon={TrendingUp} color="#10b981" />
                </div>
                <div className="animate-slide-up animate-slide-up-delay-3">
                  <StatCard label="Adherence" value={quickStats.adherence ? `${quickStats.adherence}%` : '—'} icon={Pill} color="#f59e0b" />
                </div>
                <div className="animate-slide-up animate-slide-up-delay-3">
                  <StatCard label="Appointments" value={badges.appointments || 0} icon={Calendar} color="#8b5cf6" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 shadow-md">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">HGB Trend</p>
                  <HbTrendChart key={progressKey} username={username} compact />
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 shadow-md">
                  <p className="text-xs font-semibold text-slate-500 uppercase mb-3">Today's Medications</p>
                  <MedicationTracker compact />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <button onClick={() => setView('appointments')} className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-2xl p-4 text-sm font-medium hover:scale-[1.02] transition-all duration-200 shadow-lg flex items-center gap-2">
                  <Calendar size={16} /> Book Appointment
                </button>
                <button onClick={() => setView('prescriptions')} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 text-sm font-medium text-slate-700 dark:text-slate-200 hover:scale-[1.02] transition-all duration-200 shadow-md flex items-center gap-2">
                  <FileText size={16} /> View Prescriptions
                </button>
              </div>
            </div>
          )}

          {view === 'history' && <ReportHistory username={username} role="patient" />}
          {view === 'appointments' && (
            <>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Appointments</h2>
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
              {/* My Upcoming Appointments with Cancel */}
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold text-slate-600">My Upcoming Appointments</h3>
                {myAppointments.filter(a => a.status !== 'cancelled').length === 0 && (
                  <p className="text-sm text-slate-400">No upcoming appointments</p>
                )}
                {myAppointments.filter(a => a.status !== 'cancelled').map(appt => (
                  <div key={appt.appointment_id || appt.id} className="flex items-center justify-between bg-white border rounded-lg p-3">
                    <div>
                      <p className="text-sm font-medium">{appt.slot_date} at {appt.slot_time}</p>
                      <p className="text-xs text-slate-500">Status: <span className={appt.status === 'confirmed' ? 'text-green-600' : 'text-yellow-600'}>{appt.status}</span></p>
                    </div>
                    {appt.status !== 'completed' && (
                      <button onClick={() => cancelMyAppointment(appt.appointment_id || appt.id)} className="text-xs text-red-600 hover:text-red-800 font-medium px-2 py-1 rounded hover:bg-red-50">Cancel</button>
                    )}
                  </div>
                ))}
              </div>
              <BookingModal
                isOpen={showBooking}
                onClose={() => { setShowBooking(false); setBookingSlot(null); }}
                doctors={doctors}
              />
            </>
          )}
          {view === 'medications' && <MedicationTracker />}
          {view === 'prescriptions' && <PrescriptionView />}
          {view === 'diet' && <DietFromPrescriptions />}
          {view === 'symptom' && <SymptomChecker />}
          {view === 'settings' && <ProfileSettings />}
        </div>

        <StatusFooter />
      </div>

      <Chatbot />
    </div>
  );
}
