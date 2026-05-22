import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronLeft, Check, FlaskConical } from 'lucide-react';
import client from '../api/client';

const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const CONDITIONS = ['Diabetes', 'Hypertension', 'Thyroid', 'Kidney Disease', 'Heart Disease', 'None'];
const DIETARY_PREFS = ['Vegetarian', 'Vegan', 'Non-Vegetarian', 'Pescatarian', 'Gluten-Free'];

export default function OnboardingWizard({ onComplete }) {
  const [step, setStep] = useState(0);
  const [bloodType, setBloodType] = useState('');
  const [conditions, setConditions] = useState([]);
  const [dietary, setDietary] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [selectedDoctor, setSelectedDoctor] = useState('');

  useEffect(() => {
    client.get('/api/users', { params: { role: 'doctor' } })
      .then(res => setDoctors(res.data?.users || []))
      .catch(() => {});
  }, []);

  function toggleCondition(c) {
    setConditions(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);
  }

  function toggleDietary(d) {
    setDietary(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
  }

  async function handleFinish() {
    try {
      await client.put('/api/profile', {
        blood_type: bloodType,
        conditions,
        dietary_preferences: dietary,
        linked_doctor: selectedDoctor,
        onboarding_complete: 1,
      });
    } catch {}
    onComplete?.();
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {[0, 1, 2].map(i => (
            <div key={i} className={`w-2.5 h-2.5 rounded-full transition ${step === i ? 'bg-indigo-500' : 'bg-slate-200'}`} />
          ))}
        </div>

        {/* Step 1: Health Profile */}
        {step === 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-800">Health Profile</h3>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Blood Type</label>
              <select
                value={bloodType}
                onChange={e => setBloodType(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select...</option>
                {BLOOD_TYPES.map(bt => <option key={bt} value={bt}>{bt}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Conditions</label>
              <div className="flex flex-wrap gap-2">
                {CONDITIONS.map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => toggleCondition(c)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      conditions.includes(c) ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Dietary Preferences</label>
              <div className="flex flex-wrap gap-2">
                {DIETARY_PREFS.map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => toggleDietary(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      dietary.includes(d) ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Link Doctor */}
        {step === 1 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-800">Link to a Doctor</h3>
            <p className="text-sm text-slate-500">Select a doctor to manage your care</p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {doctors.map(doc => (
                <button
                  key={doc.username}
                  onClick={() => setSelectedDoctor(doc.username)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition ${
                    selectedDoctor === doc.username
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <p className="text-sm font-medium text-slate-700">Dr. {doc.username}</p>
                  {doc.email && <p className="text-xs text-slate-400">{doc.email}</p>}
                </button>
              ))}
              {doctors.length === 0 && <p className="text-sm text-slate-400 text-center py-4">No doctors available</p>}
            </div>
          </div>
        )}

        {/* Step 3: Welcome */}
        {step === 2 && (
          <div className="text-center space-y-4 py-4">
            <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center mx-auto">
              <Check size={28} className="text-indigo-600" />
            </div>
            <h3 className="text-lg font-semibold text-slate-800">You're All Set!</h3>
            <p className="text-sm text-slate-500">Welcome to AnemiaCare. Start your first blood test to get personalized insights.</p>
            <button
              onClick={handleFinish}
              className="inline-flex items-center gap-2 bg-indigo-500 text-white font-semibold px-5 py-2.5 rounded-lg text-sm hover:bg-indigo-600 transition"
            >
              <FlaskConical size={16} /> Start First Test
            </button>
          </div>
        )}

        {/* Navigation */}
        {step < 2 && (
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => setStep(s => s - 1)}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 disabled:opacity-30"
            >
              <ChevronLeft size={14} /> Back
            </button>
            <button
              onClick={() => setStep(s => s + 1)}
              className="flex items-center gap-1 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 transition"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
