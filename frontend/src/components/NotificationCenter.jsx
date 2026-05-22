import React, { useState, useEffect } from 'react';
import { Bell, Pill, Calendar, AlertTriangle, MessageSquare, Settings, CheckCheck } from 'lucide-react';
import client from '../api/client';

const TYPES = [
  { id: 'all', label: 'All', icon: Bell },
  { id: 'medication', label: 'Medication', icon: Pill },
  { id: 'appointment', label: 'Appointment', icon: Calendar },
  { id: 'alert', label: 'Alert', icon: AlertTriangle },
  { id: 'forum', label: 'Forum', icon: MessageSquare },
  { id: 'system', label: 'System', icon: Settings },
];

const TYPE_ICONS = {
  medication: Pill,
  appointment: Calendar,
  alert: AlertTriangle,
  forum: MessageSquare,
  system: Settings,
};

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const params = { page, limit: 20 };
    if (filter !== 'all') params.type = filter;
    client.get('/api/notifications', { params })
      .then(res => setNotifications(res.data?.notifications || []))
      .catch(() => {});
  }, [filter, page]);

  async function markAsRead(id) {
    try {
      await client.put(`/api/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch {}
  }

  async function markAllRead() {
    try {
      await client.put('/api/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch {}
  }

  const filtered = filter === 'all' ? notifications : notifications.filter(n => n.type === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Notifications</h2>
        <button onClick={markAllRead} className="flex items-center gap-1.5 text-xs text-indigo-600 font-medium hover:text-indigo-800">
          <CheckCheck size={14} /> Mark All Read
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 flex-wrap">
        {TYPES.map(t => (
          <button
            key={t.id}
            onClick={() => { setFilter(t.id); setPage(1); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              filter === t.id ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <t.icon size={12} /> {t.label}
          </button>
        ))}
      </div>

      {/* Notification list */}
      <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100">
        {filtered.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-8">No notifications</p>
        )}
        {filtered.map(n => {
          const Icon = TYPE_ICONS[n.type] || Bell;
          return (
            <div
              key={n.id}
              onClick={() => !n.read && markAsRead(n.id)}
              className={`flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 transition ${!n.read ? 'bg-indigo-50/30' : ''}`}
            >
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
                <Icon size={14} className="text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${!n.read ? 'font-semibold text-slate-800' : 'text-slate-700'}`}>{n.title}</p>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
              </div>
              {!n.read && <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 mt-1.5 flex-shrink-0" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
