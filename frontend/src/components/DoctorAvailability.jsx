import React, { useState, useEffect } from 'react';
import { Save, Clock } from 'lucide-react';
import client from '../api/client';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const defaultSchedule = DAYS.map(day => ({
  day,
  available: day !== 'Saturday' && day !== 'Sunday',
  start: '09:00',
  end: '17:00',
}));

export default function DoctorAvailability() {
  const [schedule, setSchedule] = useState(defaultSchedule);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    client.get('/api/profile/available-hours')
      .then(res => {
        if (res.data?.schedule && res.data.schedule.length > 0) {
          setSchedule(res.data.schedule);
        }
      })
      .catch(() => {});
  }, []);

  function updateDay(idx, field, value) {
    setSchedule(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await client.put('/api/profile/available-hours', { schedule });
      setMessage('Schedule saved');
    } catch {
      setMessage('Failed to save');
    }
    setSaving(false);
    setTimeout(() => setMessage(null), 3000);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Clock size={18} className="text-indigo-500" />
        <h2 className="text-lg font-semibold text-slate-800">Weekly Availability</h2>
      </div>

      {message && (
        <div className={`text-sm px-3 py-2 rounded-lg ${message.includes('Failed') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
          {message}
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">Day</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase">Available</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">Start</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">End</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {schedule.map((s, idx) => (
              <tr key={s.day} className={!s.available ? 'opacity-50' : ''}>
                <td className="px-4 py-3 font-medium text-slate-700">{s.day}</td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => updateDay(idx, 'available', !s.available)}
                    className={`w-10 h-5 rounded-full transition ${s.available ? 'bg-indigo-500' : 'bg-slate-300'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${s.available ? 'translate-x-5' : 'translate-x-0.5'}`} />
                  </button>
                </td>
                <td className="px-4 py-3">
                  <input
                    type="time"
                    value={s.start}
                    onChange={e => updateDay(idx, 'start', e.target.value)}
                    disabled={!s.available}
                    className="rounded border border-slate-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
                  />
                </td>
                <td className="px-4 py-3">
                  <input
                    type="time"
                    value={s.end}
                    onChange={e => updateDay(idx, 'end', e.target.value)}
                    disabled={!s.available}
                    className="rounded border border-slate-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-2 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60"
      >
        <Save size={14} /> {saving ? 'Saving...' : 'Save Schedule'}
      </button>
    </div>
  );
}
