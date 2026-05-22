import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import client from '../api/client';

export default function BookingModal({ isOpen, onClose, doctors = [] }) {
  const [doctorId, setDoctorId] = useState('');
  const [date, setDate] = useState('');
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (doctorId && date) {
      setSlotsLoading(true);
      client.get(`/api/appointments/available-slots?doctor_id=${doctorId}&date=${date}`)
        .then(res => {
          const raw = res.data?.slots || [];
          // Handle both formats: array of strings or array of {time, available} objects
          const available = raw.map(s => typeof s === 'string' ? s : s.time).filter(Boolean);
          setSlots(available);
        })
        .catch(() => setSlots([]))
        .finally(() => setSlotsLoading(false));
    }
  }, [doctorId, date]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await client.post('/api/appointments/request', {
        doctor_id: parseInt(doctorId),
        slot_date: date,
        slot_time: selectedSlot,
        notes,
      });
      setSuccess(true);
      setTimeout(() => { onClose(); setSuccess(false); }, 1500);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to book appointment');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 relative">
        <button onClick={onClose} className="absolute top-3 right-3 text-slate-400 hover:text-slate-600">
          <X size={20} />
        </button>
        <h2 className="text-xl font-semibold mb-4">Book Appointment</h2>

        {success ? (
          <div className="text-center py-8 text-green-600 font-medium">
            ✓ Appointment requested successfully!
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Doctor</label>
              <select
                value={doctorId}
                onChange={e => setDoctorId(e.target.value)}
                className="w-full border rounded-lg px-3 py-2"
                required
              >
                <option value="">Select a doctor</option>
                {doctors.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Date</label>
              <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                className="w-full border rounded-lg px-3 py-2"
                required
              />
            </div>

            {slotsLoading && <p className="text-sm text-slate-500">Loading slots...</p>}

            {slots.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-1">Available Slots</label>
                <div className="grid grid-cols-4 gap-2">
                  {slots.map(slot => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setSelectedSlot(slot)}
                      className={`px-2 py-1 text-sm rounded border ${
                        selectedSlot === slot
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'hover:bg-indigo-50 border-slate-300'
                      }`}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium mb-1">Notes</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 h-20 resize-none"
                placeholder="Any additional notes..."
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={loading || !selectedSlot}
              className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Booking...' : 'Request Appointment'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
