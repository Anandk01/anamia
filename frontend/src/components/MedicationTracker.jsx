import React, { useState, useEffect } from 'react';
import { Pill, Check, SkipForward, Flame } from 'lucide-react';
import client from '../api/client';

export default function MedicationTracker() {
  const [meds, setMeds] = useState([]);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchSchedule = async () => {
    try {
      const res = await client.get('/api/medications/schedule');
      setMeds(res.data.medications || []);
      setStreak(res.data.streak || 0);
    } catch {
      setMeds([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSchedule(); }, []);

  const handleLog = async (id, skipped = false) => {
    try {
      await client.post(`/api/medications/${id}/log`, { skipped });
      setMeds(prev => prev.map(m =>
        m.id === id ? { ...m, taken: true, skipped, taken_at: new Date().toLocaleTimeString() } : m
      ));
    } catch (err) {
      console.error('Failed to log medication', err);
    }
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Loading medications...</div>;

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
              key={med.id}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                med.taken ? 'bg-green-50 border-green-200' : 'bg-white border-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <Pill size={20} className={med.taken ? 'text-green-600' : 'text-indigo-600'} />
                <div>
                  <p className="font-medium">{med.name}</p>
                  <p className="text-sm text-slate-500">{med.dose_mg}mg • {med.frequency}</p>
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
                    onClick={() => handleLog(med.id, false)}
                    className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200"
                    title="Take"
                  >
                    <Check size={16} />
                  </button>
                  <button
                    onClick={() => handleLog(med.id, true)}
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
