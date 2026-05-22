import React, { useState } from 'react';
import { Plus, Minus, Send } from 'lucide-react';
import client from '../api/client';

const emptyMed = { name: '', dose: '', frequency: '', duration: '' };

export default function PrescriptionForm() {
  const [patientUsername, setPatientUsername] = useState('');
  const [medications, setMedications] = useState([{ ...emptyMed }]);
  const [instructions, setInstructions] = useState('');
  const [durationDays, setDurationDays] = useState('');
  const [followUpDate, setFollowUpDate] = useState('');
  const [notes, setNotes] = useState('');
  const [dietPlan, setDietPlan] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  function addMed() {
    setMedications([...medications, { ...emptyMed }]);
  }

  function removeMed(idx) {
    if (medications.length <= 1) return;
    setMedications(medications.filter((_, i) => i !== idx));
  }

  function updateMed(idx, field, value) {
    setMedications(medications.map((m, i) => i === idx ? { ...m, [field]: value } : m));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await client.post('/api/prescriptions', {
        patient_username: patientUsername,
        medications,
        instructions,
        duration_days: parseInt(durationDays) || null,
        follow_up_date: followUpDate || null,
        notes,
        diet_plan: dietPlan,
      });
      setSuccess(true);
      setPatientUsername('');
      setMedications([{ ...emptyMed }]);
      setInstructions('');
      setDurationDays('');
      setFollowUpDate('');
      setNotes('');
      setDietPlan('');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create prescription');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Create Prescription</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Patient */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Patient Username</label>
          <input
            type="text"
            value={patientUsername}
            onChange={e => setPatientUsername(e.target.value)}
            required
            placeholder="Enter patient username"
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Medications */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Medications</label>
            <button type="button" onClick={addMed} className="flex items-center gap-1 text-xs text-indigo-600 font-medium hover:text-indigo-800">
              <Plus size={12} /> Add
            </button>
          </div>
          <div className="space-y-2">
            {medications.map((med, idx) => (
              <div key={idx} className="flex gap-2 items-center">
                <input
                  type="text"
                  placeholder="Name"
                  value={med.name}
                  onChange={e => updateMed(idx, 'name', e.target.value)}
                  required
                  className="flex-1 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Dose"
                  value={med.dose}
                  onChange={e => updateMed(idx, 'dose', e.target.value)}
                  required
                  className="w-24 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Frequency"
                  value={med.frequency}
                  onChange={e => updateMed(idx, 'frequency', e.target.value)}
                  required
                  className="w-28 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Duration"
                  value={med.duration}
                  onChange={e => updateMed(idx, 'duration', e.target.value)}
                  className="w-24 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <button type="button" onClick={() => removeMed(idx)} className="text-red-400 hover:text-red-600" disabled={medications.length <= 1}>
                  <Minus size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Instructions */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Dosage Instructions</label>
          <textarea
            value={instructions}
            onChange={e => setInstructions(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Duration & Follow-up */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Duration (days)</label>
            <input
              type="number"
              value={durationDays}
              onChange={e => setDurationDays(e.target.value)}
              min="1"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Follow-up Date</label>
            <input
              type="date"
              value={followUpDate}
              onChange={e => setFollowUpDate(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Diet Plan */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Diet Plan</label>
          <textarea
            value={dietPlan}
            onChange={e => setDietPlan(e.target.value)}
            rows={3}
            placeholder="Recommended diet, foods to eat/avoid..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Notes</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
        {success && <div className="text-sm text-green-600 bg-green-50 border border-green-200 rounded-lg px-3 py-2">Prescription created successfully!</div>}

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 transition disabled:opacity-60"
        >
          <Send size={14} /> {loading ? 'Creating...' : 'Create Prescription'}
        </button>
      </form>
    </div>
  );
}
