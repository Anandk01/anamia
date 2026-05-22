import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, CheckCircle, AlertTriangle, Shield, Activity } from 'lucide-react';
import client from '../api/client';

const STEPS = [
  { id: 'demographics', title: 'Demographics', description: 'Basic information' },
  { id: 'fatigue', title: 'Fatigue', description: 'Energy levels' },
  { id: 'symptoms1', title: 'Symptoms', description: 'Dizziness & breathlessness' },
  { id: 'symptoms2', title: 'History', description: 'Paleness & family history' },
  { id: 'diet', title: 'Diet', description: 'Dietary habits' },
];

const FATIGUE_LEVELS = [
  { value: 'none', label: 'None', description: 'I feel energetic throughout the day', color: '#10b981' },
  { value: 'mild', label: 'Mild', description: 'Slightly tired by end of day', color: '#84cc16' },
  { value: 'moderate', label: 'Moderate', description: 'Tired often, need frequent rest', color: '#f59e0b' },
  { value: 'severe', label: 'Severe', description: 'Exhausted even with minimal activity', color: '#ef4444' },
];

const DIET_TYPES = [
  { value: 'non-veg', label: 'Non-Vegetarian', description: 'Includes meat, fish, eggs', icon: '🥩' },
  { value: 'vegetarian', label: 'Vegetarian', description: 'No meat, includes dairy & eggs', icon: '🥗' },
  { value: 'vegan', label: 'Vegan', description: 'No animal products', icon: '🌱' },
];

function ProgressBar({ current, total }) {
  const pct = ((current + 1) / total) * 100;
  return (
    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
      <div
        className="h-full bg-indigo-500 rounded-full transition-all duration-500 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function YesNoCard({ label, description, value, onChange }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-slate-700">{label}</p>
      {description && <p className="text-xs text-slate-500">{description}</p>}
      <div className="flex gap-3">
        {[{ v: true, l: 'Yes' }, { v: false, l: 'No' }].map(opt => (
          <button
            key={String(opt.v)}
            type="button"
            onClick={() => onChange(opt.v)}
            className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all ${
              value === opt.v
                ? 'bg-indigo-50 border-indigo-300 text-indigo-700 ring-2 ring-indigo-100'
                : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            {opt.l}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function SymptomChecker() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({
    age: '',
    sex: '',
    fatigue: '',
    dizziness: null,
    breathlessness: null,
    paleness: null,
    familyHistory: null,
    diet: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (key, value) => setAnswers(prev => ({ ...prev, [key]: value }));

  const canProceed = () => {
    switch (step) {
      case 0: return answers.age && answers.sex;
      case 1: return answers.fatigue !== '';
      case 2: return answers.dizziness !== null && answers.breathlessness !== null;
      case 3: return answers.paleness !== null && answers.familyHistory !== null;
      case 4: return answers.diet !== '';
      default: return false;
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = {
        age: parseInt(answers.age),
        sex: answers.sex,
        fatigue: answers.fatigue,
        dizziness: answers.dizziness,
        breathlessness: answers.breathlessness,
        paleness: answers.paleness,
        family_history: answers.familyHistory,
        diet: answers.diet,
      };
      const res = await client.post('/api/predict/triage', payload);
      setResult(res.data);
    } catch (err) {
      // Fallback: compute a simple risk score locally if endpoint not available
      const riskScore = computeLocalRisk(answers);
      setResult(riskScore);
    } finally {
      setLoading(false);
    }
  };

  const computeLocalRisk = (a) => {
    let score = 0;
    if (a.fatigue === 'severe') score += 3;
    else if (a.fatigue === 'moderate') score += 2;
    else if (a.fatigue === 'mild') score += 1;
    if (a.dizziness) score += 2;
    if (a.breathlessness) score += 2;
    if (a.paleness) score += 2;
    if (a.familyHistory) score += 1;
    if (a.diet === 'vegan') score += 1;
    else if (a.diet === 'vegetarian') score += 0.5;

    let recommendation, level;
    if (score >= 7) {
      recommendation = 'Get a CBC (Complete Blood Count) test as soon as possible';
      level = 'high';
    } else if (score >= 4) {
      recommendation = 'Monitor your symptoms and consider getting a CBC test';
      level = 'medium';
    } else {
      recommendation = 'Low risk — maintain a balanced diet and stay active';
      level = 'low';
    }
    return { recommendation, level, score };
  };

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleReset = () => {
    setStep(0);
    setAnswers({ age: '', sex: '', fatigue: '', dizziness: null, breathlessness: null, paleness: null, familyHistory: null, diet: '' });
    setResult(null);
    setError('');
  };

  // Result view
  if (result) {
    const level = result.level || result.risk_level || 'low';
    const recommendation = result.recommendation || result.message || '';
    const levelConfig = {
      high: { color: '#ef4444', bg: '#fef2f2', icon: AlertTriangle, label: 'High Risk', border: '#fecaca' },
      medium: { color: '#f59e0b', bg: '#fffbeb', icon: Activity, label: 'Moderate Risk', border: '#fde68a' },
      low: { color: '#10b981', bg: '#ecfdf5', icon: Shield, label: 'Low Risk', border: '#a7f3d0' },
    };
    const config = levelConfig[level] || levelConfig.low;
    const Icon = config.icon;

    return (
      <div className="max-w-lg mx-auto">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 text-center" style={{ backgroundColor: config.bg }}>
            <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center" style={{ backgroundColor: `${config.color}20` }}>
              <Icon size={32} style={{ color: config.color }} />
            </div>
            <h2 className="text-xl font-bold text-slate-800 mb-1">{config.label}</h2>
            <p className="text-sm text-slate-600">{recommendation}</p>
          </div>

          <div className="p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase">Your Responses</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Age</span>
                <p className="font-medium text-slate-700">{answers.age}</p>
              </div>
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Sex</span>
                <p className="font-medium text-slate-700 capitalize">{answers.sex}</p>
              </div>
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Fatigue</span>
                <p className="font-medium text-slate-700 capitalize">{answers.fatigue}</p>
              </div>
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Diet</span>
                <p className="font-medium text-slate-700 capitalize">{answers.diet}</p>
              </div>
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Dizziness</span>
                <p className="font-medium text-slate-700">{answers.dizziness ? 'Yes' : 'No'}</p>
              </div>
              <div className="bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-500 text-xs">Family History</span>
                <p className="font-medium text-slate-700">{answers.familyHistory ? 'Yes' : 'No'}</p>
              </div>
            </div>

            {level === 'high' && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                <strong>Recommended:</strong> Schedule a CBC test with your doctor. You can book an appointment from the Appointments section.
              </div>
            )}

            <button
              onClick={handleReset}
              className="w-full mt-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
            >
              Check Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading view
  if (loading) {
    return (
      <div className="max-w-lg mx-auto">
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <div className="animate-spin w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full mx-auto mb-4" />
          <p className="text-sm text-slate-600">Analyzing your symptoms...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-1">Symptom Checker</h2>
        <p className="text-sm text-slate-500">Answer a few questions to assess your anemia risk</p>
      </div>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-500">Step {step + 1} of {STEPS.length}</span>
          <span className="text-xs text-slate-400">{STEPS[step].title}</span>
        </div>
        <ProgressBar current={step} total={STEPS.length} />
        <div className="flex justify-between mt-2">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={`w-2 h-2 rounded-full transition-all ${
                i <= step ? 'bg-indigo-500' : 'bg-slate-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 min-h-[280px] flex flex-col">
        <div className="flex-1">
          {/* Step 0: Demographics */}
          {step === 0 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-slate-800">Tell us about yourself</h3>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
                <input
                  type="number"
                  value={answers.age}
                  onChange={e => update('age', e.target.value)}
                  placeholder="Enter your age"
                  min="1"
                  max="120"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Sex</label>
                <div className="flex gap-3">
                  {['male', 'female'].map(s => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => update('sex', s)}
                      className={`flex-1 py-2.5 rounded-lg border text-sm font-medium capitalize transition-all ${
                        answers.sex === s
                          ? 'bg-indigo-50 border-indigo-300 text-indigo-700 ring-2 ring-indigo-100'
                          : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Fatigue */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-slate-800">How would you describe your fatigue level?</h3>
              <div className="space-y-2">
                {FATIGUE_LEVELS.map(f => (
                  <button
                    key={f.value}
                    type="button"
                    onClick={() => update('fatigue', f.value)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
                      answers.fatigue === f.value
                        ? 'border-indigo-300 bg-indigo-50 ring-2 ring-indigo-100'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: f.color }} />
                      <div>
                        <p className="text-sm font-medium text-slate-700">{f.label}</p>
                        <p className="text-xs text-slate-500">{f.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Dizziness & Breathlessness */}
          {step === 2 && (
            <div className="space-y-5">
              <h3 className="text-base font-semibold text-slate-800">Do you experience any of these?</h3>
              <YesNoCard
                label="Dizziness or lightheadedness"
                description="Feeling faint, especially when standing up quickly"
                value={answers.dizziness}
                onChange={v => update('dizziness', v)}
              />
              <YesNoCard
                label="Shortness of breath"
                description="Difficulty breathing during normal activities"
                value={answers.breathlessness}
                onChange={v => update('breathlessness', v)}
              />
            </div>
          )}

          {/* Step 3: Paleness & Family History */}
          {step === 3 && (
            <div className="space-y-5">
              <h3 className="text-base font-semibold text-slate-800">A few more questions</h3>
              <YesNoCard
                label="Noticeable paleness"
                description="Pale skin, nail beds, or inner eyelids"
                value={answers.paleness}
                onChange={v => update('paleness', v)}
              />
              <YesNoCard
                label="Family history of anemia"
                description="Any blood relatives diagnosed with anemia"
                value={answers.familyHistory}
                onChange={v => update('familyHistory', v)}
              />
            </div>
          )}

          {/* Step 4: Diet */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-slate-800">What best describes your diet?</h3>
              <div className="space-y-2">
                {DIET_TYPES.map(d => (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => update('diet', d.value)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
                      answers.diet === d.value
                        ? 'border-indigo-300 bg-indigo-50 ring-2 ring-indigo-100'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{d.icon}</span>
                      <div>
                        <p className="text-sm font-medium text-slate-700">{d.label}</p>
                        <p className="text-xs text-slate-500">{d.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-600 mt-3">{error}</p>}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-100">
          <button
            onClick={handleBack}
            disabled={step === 0}
            className="flex items-center gap-1 px-4 py-2 text-sm text-slate-600 hover:text-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            <ChevronLeft size={16} /> Back
          </button>
          <button
            onClick={handleNext}
            disabled={!canProceed()}
            className="flex items-center gap-1 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {step === STEPS.length - 1 ? 'Get Results' : 'Next'} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
