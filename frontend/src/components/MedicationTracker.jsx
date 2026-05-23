import React, { useState, useEffect } from 'react';
import { Pill, Check, SkipForward, Flame, Clock } from 'lucide-react';
import client from '../api/client';
import { useSocket } from '../contexts/SocketContext';

function getMedTimes(frequency, reminderTimes) {
  // If reminder_times is provided, use those
  if (reminderTimes) {
    try {
      const times = typeof reminderTimes === 'string' ? JSON.parse(reminderTimes) : reminderTimes;
      if (Array.isArray(times) && times.length > 0) {
        return times.map(t => {
          const [h, m] = t.split(':');
          const hour = parseInt(h);
          const ampm = hour >= 12 ? 'PM' : 'AM';
          const h12 = hour % 12 || 12;
          return `${h12}:${m} ${ampm}`;
        }).join(', ');
      }
    } catch {}
  }
  // Fallback to frequency-based times
  switch (frequency) {
    case 'daily': return '8:00 AM';
    case 'twice': return '8:00 AM, 8:00 PM';
    case 'thrice': return '8:00 AM, 2:00 PM, 8:00 PM';
    case 'weekly': return 'Every Monday 8:00 AM';
    default: return '8:00 AM';
  }
}

export default function MedicationTracker({ compact }) {
  const [meds, setMeds] = useState([]);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const { addListener, removeListener } = useSocket() || {};

  const fetchSchedule = async () => {
    try {
      const res = await client.get('/api/medications/schedule');
      const schedule = res.data.schedule || res.data.medications || [];
      setMeds(schedule);
      setStreak(res.data.streak || 0);
    } catch {
      setMeds([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSchedule(); }, []);

  // Listen for new prescriptions via socket
  useEffect(() => {
    if (!addListener) return;
    const handleNewPrescription = () => {
      fetchSchedule(); // Refresh the list
    };
    addListener('new_prescription', handleNewPrescription);
    return () => {
      if (removeListener) removeListener('new_prescription', handleNewPrescription);
    };
  }, [addListener, removeListener]);

  const handleLog = async (id, skipped = false) => {
    try {
      await client.post(`/api/medications/${id}/log`, { skipped });
      setMeds(prev => prev.map(m =>
        m.med_id === id ? { ...m, taken: true, skipped, taken_at: new Date().toLocaleTimeString() } : m
      ));
    } catch (err) {
      console.error('Failed to log medication', err);
    }
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Loading medications...</div>;

  if (compact) {
    return (
      <div className="space-y-2">
        {meds.length === 0 && <p className="text-sm text-slate-400">No medications today</p>}
        {meds.slice(0, 3).map(med => (
          <div key={med.med_id} className="flex items-center gap-2 text-sm">
            <Pill size={14} className={med.taken ? 'text-green-600' : 'text-indigo-600'} />
            <span className="truncate">{med.name} {med.dose_mg}{med.dose_unit || 'mg'}</span>
            {med.taken && <Check size={14} className="text-green-600" />}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Today's Medications</h2>
        <div className="flex items-center gap-1 text-orange-600 font-medium">
          <Flame size={18} />
          <span>{streak} days</span>
        </div>
      </div>

      {meds.length === 0 ? (
        <p className="text-slate-500 text-sm">No medications scheduled for today</p>
      ) : (
        <div className="space-y-3">
          {meds.map(med => (
            <div
              key={med.med_id}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                med.taken ? 'bg-green-50 border-green-200' : 'bg-white border-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <Pill size={20} className={med.taken ? 'text-green-600' : 'text-indigo-600'} />
                <div>
                  <p className="font-medium">{med.name}</p>
                  <p className="text-sm text-slate-500">{med.dose_mg}{med.dose_unit || 'mg'} • {med.frequency}</p>
                  <p className="text-xs text-indigo-500 flex items-center gap-1 mt-0.5">
                    <Clock size={11} /> {getMedTimes(med.frequency, med.reminder_times)}
                  </p>
                </div>
              </div>

              {med.taken ? (
                <div className="flex items-center gap-1 text-green-600 text-sm">
                  <Check size={16} />
                  <span>{med.taken_at}</span>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleLog(med.med_id, false)}
                    className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200"
                    title="Take"
                  >
                    <Check size={16} />
                  </button>
                  <button
                    onClick={() => handleLog(med.med_id, true)}
                    className="p-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200"
                    title="Skip"
                  >
                    <SkipForward size={16} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
