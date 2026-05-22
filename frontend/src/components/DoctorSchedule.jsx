import React, { useState, useEffect } from 'react';
import { Check, X, Clock, User } from 'lucide-react';
import client from '../api/client';

export default function DoctorSchedule() {
  const [pending, setPending] = useState([]);
  const [confirmed, setConfirmed] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAppointments = async () => {
    try {
      const res = await client.get('/api/appointments/calendar?week_start=' + getThisWeek());
      const appts = res.data.appointments || [];
      setPending(appts.filter(a => a.status === 'pending'));
      setConfirmed(appts.filter(a => a.status === 'confirmed'));
    } catch {
      setPending([]);
      setConfirmed([]);
    } finally {
      setLoading(false);
    }
  };

  function getThisWeek() {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    return d.toISOString().split('T')[0];
  }

  useEffect(() => { fetchAppointments(); }, []);

  const handleAccept = async (id) => {
    await client.put(`/api/appointments/${id}/confirm`);
    fetchAppointments();
  };

  const handleDecline = async (id) => {
    await client.put(`/api/appointments/${id}/cancel`);
    fetchAppointments();
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Loading schedule...</div>;

  return (
    <div className="space-y-6">
      {/* Pending Requests */}
      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Clock size={18} className="text-yellow-600" />
          Pending Requests ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <p className="text-slate-500 text-sm">No pending requests</p>
        ) : (
          <div className="space-y-3">
            {pending.map(appt => (
              <div key={appt.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium flex items-center gap-1">
                    <User size={14} /> {appt.patient_name || 'Patient'}
                  </p>
                  <p className="text-sm text-slate-600">{appt.date} at {appt.time}</p>
                  {appt.notes && <p className="text-sm text-slate-500 mt-1">{appt.notes}</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAccept(appt.id)}
                    className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200"
                    title="Accept"
                  >
                    <Check size={18} />
                  </button>
                  <button
                    onClick={() => handleDecline(appt.id)}
                    className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
                    title="Decline"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Confirmed Appointments */}
      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Check size={18} className="text-green-600" />
          Confirmed Appointments ({confirmed.length})
        </h2>
        {confirmed.length === 0 ? (
          <p className="text-slate-500 text-sm">No confirmed appointments</p>
        ) : (
          <div className="space-y-2">
            {confirmed.map(appt => (
              <div key={appt.id} className="bg-white border rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="font-medium">{appt.patient_name || 'Patient'}</p>
                  <p className="text-sm text-slate-600">{appt.date} at {appt.time}</p>
                </div>
                <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">
                  Confirmed
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
