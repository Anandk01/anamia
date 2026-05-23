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
  const [doctorSchedule, setDoctorSchedule] = useState(null);
  const [dayUnavailableMsg, setDayUnavailableMsg] = useState('');

  // Fetch doctor's weekly schedule when doctor is selected
  useEffect(() => {
    if (doctorId) {
      client.get(`/api/appointments/doctor-schedule/${doctorId}`)
        .then(res => setDoctorSchedule(res.data))
        .catch(() => setDoctorSchedule(null));
    } else {
      setDoctorSchedule(null);
    }
  }, [doctorId]);

  // Fetch available slots when doctor and date are selected
  useEffect(() => {
    if (doctorId && date) {
      // Check if the selected day is available
      if (doctorSchedule && doctorSchedule.available_days?.length > 0) {
        const dayMap = { 0: 'sun', 1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri', 6: 'sat' };
        const selectedDay = dayMap[new Date(date).getDay()];
        if (!doctorSchedule.available_days.includes(selectedDay)) {
          setDayUnavailableMsg('Doctor is not available on this day. Please select another date.');
          setSlots([]);
          setSelectedSlot('');
          return;
        }
      }
      setDayUnavailableMsg('');
      setSlotsLoading(true);
      setSelectedSlot('');
      client.get(`/api/appointments/available-slots?doctor_id=${doctorId}&date=${date}`)
        .then(res => setSlots(res.data?.slots || []))
        .catch(() => setSlots([]))
        .finally(() => setSlotsLoading(false));
    } else {
      setSlots([]);
      setDayUnavailableMsg('');
    }
  }, [doctorId, date, doctorSchedule]);

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
      setError(err.response?.data?.error || err.response?.data?.message || 'Failed to book appointment');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 relative max-h-[90vh] overflow-y-auto">
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
              {doctorSchedule && doctorSchedule.available_days?.length > 0 && (
                <p className="text-xs text-indigo-600 mt-1">
                  Available: {doctorSchedule.available_days.map(d => d.charAt(0).toUpperCase() + d.slice(1)).join(', ')}
                </p>
              )}
              {doctorSchedule && doctorSchedule.available_days?.length === 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  Doctor has not set availability yet (default: Mon–Fri 9AM–5PM)
                </p>
              )}
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
              {dayUnavailableMsg && (
                <p className="text-xs text-red-600 mt-1">{dayUnavailableMsg}</p>
              )}
            </div>

            {slotsLoading && <p className="text-sm text-slate-500">Loading slots...</p>}

            {slots.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-1">Available Slots</label>
                <div className="grid grid-cols-4 gap-2">
                  {slots.map(slot => {
                    const isAvailable = typeof slot === 'object' ? slot.available : true;
                    const time = typeof slot === 'object' ? slot.time : slot;
                    return (
                      <button
                        key={time}
                        type="button"
                        onClick={() => isAvailable && setSelectedSlot(time)}
                        disabled={!isAvailable}
                        className={`px-2 py-1 text-sm rounded border ${
                          selectedSlot === time
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : !isAvailable
                              ? 'bg-red-50 text-red-400 border-red-200 cursor-not-allowed'
                              : 'hover:bg-indigo-50 border-slate-300'
                        }`}
                      >
                        {time}
                      </button>
                    );
                  })}
                </div>
                {slots.every(s => typeof s === 'object' && !s.available) && (
                  <p className="text-xs text-red-600 mt-2">All slots are fully booked for this date.</p>
                )}
              </div>
            )}

            {!slotsLoading && slots.length === 0 && doctorId && date && !dayUnavailableMsg && (
              <p className="text-sm text-slate-500">No slots available for this date.</p>
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
