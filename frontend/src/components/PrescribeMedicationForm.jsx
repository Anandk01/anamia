import React, { useState, useEffect } from 'react';
import client from '../api/client';

export default function PrescribeMedicationForm({ patientUsername, predictionId, onClose }) {
  const [form, setForm] = useState({
    name: '',
    dose_mg: '',
    dose_unit: 'mg',
    frequency: 'daily',
    reminder_times: ['08:00'],
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Patient bio panel state
  const [patientProfile, setPatientProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState('');

  // Debounced fetch of patient profile when patientUsername changes
  useEffect(() => {
    if (!patientUsername || patientUsername.length < 2) {
      setPatientProfile(null);
      setProfileError('');
      return;
    }
    const timer = setTimeout(() => {
      setProfileLoading(true);
      setProfileError('');
      client.get(`/api/profile/${patientUsername}`)
        .then(res => {
          setPatientProfile(res.data?.profile || null);
          setProfileError('');
        })
        .catch(err => {
          setPatientProfile(null);
          // Don't show error — patient may exist but not have profile filled yet
          setProfileError('');
        })
        .finally(() => setProfileLoading(false));
    }, 500);
    return () => clearTimeout(timer);
  }, [patientUsername]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await client.post('/api/medications/prescribe', {
        patient_username: patientUsername,
        prediction_id: predictionId || null,
        name: form.name,
        dose_mg: parseFloat(form.dose_mg),
        dose_unit: form.dose_unit,
        frequency: form.frequency,
        reminder_times: form.reminder_times.filter(t => t),
        start_date: form.start_date,
        end_date: form.end_date || null,
        notes: form.notes || null,
      });
      setSuccess(true);
      setTimeout(() => onClose(), 1500);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to prescribe');
    } finally {
      setSubmitting(false);
    }
  };

  const addReminderTime = () => setForm(f => ({ ...f, reminder_times: [...f.reminder_times, ''] }));
  const removeReminderTime = (idx) => setForm(f => ({ ...f, reminder_times: f.reminder_times.filter((_, i) => i !== idx) }));
  const updateReminderTime = (idx, val) => setForm(f => ({ ...f, reminder_times: f.reminder_times.map((t, i) => i === idx ? val : t) }));

  if (success) {
    return (
      <div className="text-center py-8">
        <p className="text-green-600 font-medium">Prescription sent to {patientUsername}!</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-sm text-slate-500">Prescribing for: <strong>{patientUsername}</strong></p>

      {/* Patient Bio Panel */}
      {profileLoading && <p className="text-xs text-slate-400 mt-1">Loading patient info...</p>}
      {profileError && <p className="text-xs text-red-500 mt-1">{profileError}</p>}
      {patientProfile && (
        <div className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
          <p className="font-semibold text-slate-700">{patientProfile.username}</p>
          <p className="text-slate-500">
            Age: {patientProfile.age || '—'} | Sex: {patientProfile.sex === 1 ? 'Female' : patientProfile.sex === 0 ? 'Male' : '—'}
          </p>
          <p className="text-slate-500">Blood Type: {patientProfile.blood_type || '—'}</p>
          {patientProfile.known_conditions && patientProfile.known_conditions.length > 0 && (
            <p className="text-slate-500">Conditions: {Array.isArray(patientProfile.known_conditions) ? patientProfile.known_conditions.join(', ') : patientProfile.known_conditions}</p>
          )}
          {patientProfile.dietary_preferences && patientProfile.dietary_preferences.length > 0 && (
            <p className="text-slate-500">Diet: {Array.isArray(patientProfile.dietary_preferences) ? patientProfile.dietary_preferences.join(', ') : patientProfile.dietary_preferences}</p>
          )}
        </div>
      )}

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Medicine Name *</label>
        <input type="text" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. Iron Tablet" />
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">Dose *</label>
          <input type="number" required step="0.1" value={form.dose_mg} onChange={e => setForm(f => ({ ...f, dose_mg: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="100" />
        </div>
        <div className="w-24">
          <label className="block text-xs font-medium text-slate-600 mb-1">Unit</label>
          <select value={form.dose_unit} onChange={e => setForm(f => ({ ...f, dose_unit: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm">
            <option value="mg">mg</option>
            <option value="ml">ml</option>
            <option value="IU">IU</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Frequency *</label>
        <select value={form.frequency} onChange={e => setForm(f => ({ ...f, frequency: e.target.value }))}
          className="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="daily">Once Daily</option>
          <option value="twice">Twice Daily</option>
          <option value="thrice">Three Times Daily</option>
          <option value="weekly">Weekly</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Reminder Times</label>
        {form.reminder_times.map((t, idx) => (
          <div key={idx} className="flex gap-2 mb-1">
            <input type="time" value={t} onChange={e => updateReminderTime(idx, e.target.value)}
              className="flex-1 border rounded-lg px-3 py-1.5 text-sm" />
            {form.reminder_times.length > 1 && (
              <button type="button" onClick={() => removeReminderTime(idx)} className="text-red-500 text-sm px-2">✕</button>
            )}
          </div>
        ))}
        <button type="button" onClick={addReminderTime} className="text-xs text-indigo-600 hover:underline">+ Add time</button>
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">Start Date *</label>
          <input type="date" required value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
          <input type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Notes</label>
        <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Take with food..." />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="flex gap-2 pt-2">
        <button type="submit" disabled={submitting}
          className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
          {submitting ? 'Prescribing...' : 'Prescribe'}
        </button>
        <button type="button" onClick={onClose}
          className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
          Cancel
        </button>
      </div>
    </form>
  );
}
