import React, { useState } from 'react';
import { Pill } from 'lucide-react';
import client from '../api/client';

export default function PrescribeMedication() {
  const [form, setForm] = useState({
    patient_username: '',
    medication_name: '',
    dose_mg: '',
    frequency: 'daily',
    start_date: '',
    end_date: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await client.post('/api/medications', {
        ...form,
        dose_mg: Number(form.dose_mg),
      });
      setSuccess(`Prescribed ${form.medication_name} to ${form.patient_username}`);
      setForm({ patient_username: '', medication_name: '', dose_mg: '', frequency: 'daily', start_date: '', end_date: '' });
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to prescribe medication');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 max-w-lg">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Pill size={20} className="text-indigo-600" />
        Prescribe Medication
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Patient Username</label>
          <input
            name="patient_username"
            value={form.patient_username}
            onChange={handleChange}
            className="w-full border rounded-lg px-3 py-2"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Medication Name</label>
          <input
            name="medication_name"
            value={form.medication_name}
            onChange={handleChange}
            className="w-full border rounded-lg px-3 py-2"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Dose (mg)</label>
            <input
              name="dose_mg"
              type="number"
              value={form.dose_mg}
              onChange={handleChange}
              className="w-full border rounded-lg px-3 py-2"
              min="1"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Frequency</label>
            <select
              name="frequency"
              value={form.frequency}
              onChange={handleChange}
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="daily">Daily</option>
              <option value="twice">Twice daily</option>
              <option value="thrice">Thrice daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Start Date</label>
            <input
              name="start_date"
              type="date"
              value={form.start_date}
              onChange={handleChange}
              className="w-full border rounded-lg px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">End Date (optional)</label>
            <input
              name="end_date"
              type="date"
              value={form.end_date}
              onChange={handleChange}
              className="w-full border rounded-lg px-3 py-2"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-green-600">{success}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Prescribing...' : 'Prescribe'}
        </button>
      </form>
    </div>
  );
}
