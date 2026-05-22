import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import client from '../api/client';
import { useAuth } from '../hooks/useAuth';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const SLOTS = [];
for (let h = 9; h < 17; h++) {
  SLOTS.push(`${String(h).padStart(2, '0')}:00`);
  SLOTS.push(`${String(h).padStart(2, '0')}:30`);
}

function getWeekStart(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatDate(d) {
  return d.toISOString().split('T')[0];
}

const STATUS_COLORS = {
  pending: 'bg-yellow-200 border-yellow-400',
  confirmed: 'bg-green-200 border-green-400',
  cancelled: 'bg-slate-200 border-slate-400',
};

export default function AppointmentCalendar({ onSlotClick, onAppointmentClick }) {
  const [weekStart, setWeekStart] = useState(getWeekStart(new Date()));
  const [appointments, setAppointments] = useState([]);
  const { getRole } = useAuth();
  const role = getRole();

  useEffect(() => {
    client.get(`/api/appointments/calendar?week_start=${formatDate(weekStart)}`)
      .then(res => setAppointments(res.data.appointments || []))
      .catch(() => setAppointments([]));
  }, [weekStart]);

  const prevWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    setWeekStart(d);
  };

  const nextWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    setWeekStart(d);
  };

  const getAppointment = (dayIdx, time) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + dayIdx);
    const dateStr = formatDate(date);
    return appointments.find(a => a.date === dateStr && a.time === time);
  };

  const handleCellClick = (dayIdx, time) => {
    const appt = getAppointment(dayIdx, time);
    if (appt) {
      onAppointmentClick?.(appt);
    } else if (role === 'patient') {
      const date = new Date(weekStart);
      date.setDate(date.getDate() + dayIdx);
      onSlotClick?.({ date: formatDate(date), time });
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <button onClick={prevWeek} className="p-2 hover:bg-slate-100 rounded">
          <ChevronLeft size={20} />
        </button>
        <h3 className="font-semibold text-lg">
          Week of {formatDate(weekStart)}
        </h3>
        <button onClick={nextWeek} className="p-2 hover:bg-slate-100 rounded">
          <ChevronRight size={20} />
        </button>
      </div>

      <div className="grid grid-cols-8 gap-px bg-slate-200 rounded overflow-hidden text-xs">
        {/* Header row */}
        <div className="bg-slate-50 p-2 font-medium text-center">Time</div>
        {DAYS.map(day => (
          <div key={day} className="bg-slate-50 p-2 font-medium text-center">{day}</div>
        ))}

        {/* Time slots */}
        {SLOTS.map(time => (
          <React.Fragment key={time}>
            <div className="bg-white p-1 text-center text-slate-600 border-t">{time}</div>
            {DAYS.map((_, dayIdx) => {
              const appt = getAppointment(dayIdx, time);
              return (
                <div
                  key={`${dayIdx}-${time}`}
                  onClick={() => handleCellClick(dayIdx, time)}
                  className={`bg-white border-t p-1 cursor-pointer hover:bg-indigo-50 min-h-[28px] ${
                    appt ? `${STATUS_COLORS[appt.status] || ''} border-l-2` : ''
                  }`}
                >
                  {appt && <span className="truncate block">{appt.patient_name || appt.title || '•'}</span>}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
