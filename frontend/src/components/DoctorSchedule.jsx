import React, { useState, useEffect } from 'react';
import { Check, X, Clock, User, RefreshCw } from 'lucide-react';
import client from '../api/client';

export default function DoctorSchedule({ compact }) {
  const [pending, setPending] = useState([]);
  const [confirmed, setConfirmed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rescheduleId, setRescheduleId] = useState(null);
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [reason, setReason] = useState('');

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

  // Helper to get the appointment ID regardless of field name
  const getId = (appt) => appt.appointment_id || appt.id;
  const getDate = (appt) => appt.slot_date || appt.date;
  const getTime = (appt) => appt.slot_time || appt.time;
  const getPatient = (appt) => appt.patient_username || appt.patient_name || 'Patient';

  useEffect(() => { fetchAppointments(); }, []);

  const handleAccept = async (appt) => {
    try {
      await client.put(`/api/appointments/${getId(appt)}/confirm`);
      fetchAppointments();
    } catch (err) {
      console.error('Accept failed', err);
    }
  };

  const handleDecline = async (appt) => {
    try {
      await client.put(`/api/appointments/${getId(appt)}/cancel`, { reason: 'Declined by doctor' });
      fetchAppointments();
    } catch (err) {
      console.error('Decline failed', err);
    }
  };

  const handleReschedule = async (appt) => {
    if (!newDate || !newTime) return;
    try {
      await client.put(`/api/appointments/${getId(appt)}/reschedule`, { new_date: newDate, new_time: newTime, reason });
      setRescheduleId(null);
      setNewDate(''); setNewTime(''); setReason('');
      fetchAppointments();
    } catch (err) {
      console.error('Reschedule failed', err);
    }
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Loading schedule...</div>;

  if (compact) {
    return (
      <div className="space-y-2">
        {pending.length === 0 && confirmed.length === 0 && <p className="text-sm text-slate-400">No appointments today</p>}
        {pending.slice(0, 3).map(appt => (
          <div key={getId(appt)} className="flex items-center justify-between text-sm py-1.5 border-b border-slate-50">
            <span className="text-slate-700">{getPatient(appt)} — {getTime(appt)}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">Pending</span>
          </div>
        ))}
        {confirmed.slice(0, 3).map(appt => (
          <div key={getId(appt)} className="flex items-center justify-between text-sm py-1.5 border-b border-slate-50">
            <span className="text-slate-700">{getPatient(appt)} — {getTime(appt)}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Confirmed</span>
          </div>
        ))}
      </div>
    );
  }

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
              <div key={getId(appt)} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium flex items-center gap-1">
                      <User size={14} /> {getPatient(appt)}
                    </p>
                    <p className="text-sm text-slate-600">{getDate(appt)} at {getTime(appt)}</p>
                    {appt.notes && <p className="text-sm text-slate-500 mt-1">{appt.notes}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleAccept(appt)} className="p-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200" title="Accept">
                      <Check size={18} />
                    </button>
                    <button onClick={() => handleDecline(appt)} className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200" title="Decline">
                      <X size={18} />
                    </button>
                    <button onClick={() => setRescheduleId(rescheduleId === getId(appt) ? null : getId(appt))} className="p-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200" title="Reschedule">
                      <RefreshCw size={18} />
                    </button>
                  </div>
                </div>
                {rescheduleId === getId(appt) && (
                  <div className="mt-3 p-3 bg-white border border-blue-200 rounded-lg space-y-2">
                    <p className="text-xs font-semibold text-blue-700 uppercase">Reschedule To</p>
                    <div className="flex gap-2">
                      <input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} className="flex-1 rounded border border-slate-200 px-2 py-1.5 text-sm" />
                      <input type="time" value={newTime} onChange={e => setNewTime(e.target.value)} className="w-28 rounded border border-slate-200 px-2 py-1.5 text-sm" />
                    </div>
                    <input type="text" value={reason} onChange={e => setReason(e.target.value)} placeholder="Reason (optional)" className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm" />
                    <button onClick={() => handleReschedule(appt)} className="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded hover:bg-blue-600">
                      Confirm Reschedule
                    </button>
                  </div>
                )}
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
              <div key={getId(appt)} className="bg-white border rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="font-medium">{getPatient(appt)}</p>
                  <p className="text-sm text-slate-600">{getDate(appt)} at {getTime(appt)}</p>
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
