import React, { useState, useEffect, useRef } from 'react';
import { Bell, MessageSquare, Calendar, AlertTriangle, Info } from 'lucide-react';
import client from '../api/client';

const TYPE_ICONS = {
  medication: MessageSquare,
  appointment: Calendar,
  alert: AlertTriangle,
  default: Info,
};

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    client.get('/api/notifications/unread-count')
      .then(res => setUnreadCount(res.data?.count || 0))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (open) {
      client.get('/api/notifications', { params: { page: 1, limit: 5 } })
        .then(res => setNotifications(res.data?.notifications || []))
        .catch(() => {});
    }
  }, [open]);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 rounded-lg hover:bg-slate-100 transition"
        aria-label="Notifications"
      >
        <Bell size={18} className="text-slate-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border border-slate-200 z-50 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-700">Notifications</span>
            <span className="text-xs text-slate-400">{unreadCount} unread</span>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 && (
              <p className="text-sm text-slate-400 text-center py-6">No notifications</p>
            )}
            {notifications.map(n => {
              const Icon = TYPE_ICONS[n.type] || TYPE_ICONS.default;
              return (
                <div key={n.id} className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 border-b border-slate-50">
                  <Icon size={16} className="text-indigo-500 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 font-medium truncate">{n.title}</p>
                    <p className="text-xs text-slate-400">{timeAgo(n.created_at)}</p>
                  </div>
                  {!n.read && <span className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5 flex-shrink-0" />}
                </div>
              );
            })}
          </div>
          <a href="#notifications" className="block text-center text-xs text-indigo-600 font-medium py-2.5 border-t border-slate-100 hover:bg-slate-50">
            View All
          </a>
        </div>
      )}
    </div>
  );
}
