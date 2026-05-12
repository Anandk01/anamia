import { useState } from 'react';

// ─── All 8 questions in interview order ───────────────────────────────────────
// Each question maps to the exact key the Flask /triage endpoint expects.
const QUESTIONS = [
  {
    key:      'Age',
    type:     'number',
    question: "What is the patient's age?",
    hint:     'Enter a number between 1 and 120',
  },
  {
    key:      'Sex',
    type:     'choice',
    question: "What is the patient's biological sex?",
    options:  [{ label: 'Male', value: 0 }, { label: 'Female', value: 1 }],
  },
  {
    key:      'Family_History_Anemia',
    type:     'choice',
    question: 'Does the patient have a family history of anemia?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
  {
    key:      'Vegan_Diet',
    type:     'choice',
    question: 'Does the patient follow a vegan or strictly plant-based diet?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
  {
    key:      'Fatigue',
    type:     'choice',
    question: 'Does the patient report persistent fatigue or tiredness?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
  {
    key:      'Dizziness',
    type:     'choice',
    question: 'Does the patient experience dizziness or lightheadedness?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
  {
    key:      'Breathlessness',
    type:     'choice',
    question: 'Does the patient feel short of breath during normal activity?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
  {
    key:      'Paleness',
    type:     'choice',
    question: 'Is there visible paleness of the skin, lips, or inner eyelids?',
    options:  [{ label: 'Yes', value: 1 }, { label: 'No', value: 0 }],
  },
];

const TOTAL = QUESTIONS.length;

export default function PatientTriage() {
  const [open,    setOpen]    = useState(false);   // whether the modal is visible
  const [stage,   setStage]   = useState('prompt'); // 'prompt' | 'interview' | 'result'
  const [qIndex,  setQIndex]  = useState(0);       // current question index (0–7)
  const [answers, setAnswers] = useState({});       // { Age: 35, Sex: 0, ... }
  const [ageInput, setAgeInput] = useState('');    // controlled value for the Age text input
  const [result,  setResult]  = useState(null);    // { needs_test: bool } from Flask
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const current = QUESTIONS[qIndex];
  const isLast  = qIndex === TOTAL - 1;

  // ─── Open / reset ─────────────────────────────────────────────────────────
  function handleOpen() {
    setOpen(true);
    setStage('prompt');
    setQIndex(0);
    setAnswers({});
    setAgeInput('');
    setResult(null);
    setError(null);
  }

  function handleStartInterview() {
    setStage('interview');
    setQIndex(0);
    setAnswers({});
    setAgeInput('');
  }

  function handleClose() {
    setOpen(false);
    setStage('prompt');
  }

  function handleNewAssessment() {
    setOpen(true);
    setStage('prompt');
    setQIndex(0);
    setAnswers({});
    setAgeInput('');
    setResult(null);
    setError(null);
  }

  // ─── Record answer and advance ────────────────────────────────────────────
  function recordAndAdvance(value) {
    const updated = { ...answers, [current.key]: value };
    setAnswers(updated);

    if (isLast) {
      submitToAPI(updated);
    } else {
      setQIndex(i => i + 1);
    }
  }

  // For the Age number input — advance on Enter or Next button
  function handleAgeNext() {
    const val = parseInt(ageInput, 10);
    if (!ageInput || isNaN(val) || val < 1 || val > 120) return;
    recordAndAdvance(val);
    setAgeInput('');
  }

  // ─── API call ─────────────────────────────────────────────────────────────
  async function submitToAPI(finalAnswers) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/triage', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(finalAnswers),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Server error: ${response.status}`);
      setResult(data);
      setStage('result');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ─── Progress bar ─────────────────────────────────────────────────────────
  const progress = Math.round(((qIndex) / TOTAL) * 100);

  // ══════════════════════════════════════════════════════════════════════════
  // CLOSED STATE — shown when modal is not open
  // ══════════════════════════════════════════════════════════════════════════
  if (!open) {
    return (
      <div className="bg-slate-50 border border-dashed border-slate-300 rounded-2xl px-6 py-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-700">
            Don't have test reports?
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            Want to check if a CBC test is needed? Answer a few quick questions.
          </p>
        </div>
        <button
          onClick={handleOpen}
          className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow-sm"
        >
          Start Check →
        </button>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PROMPT STAGE — ask if user wants to proceed
  // ══════════════════════════════════════════════════════════════════════════
  if (stage === 'prompt') {
    return (
      <div className="bg-white rounded-2xl shadow-md border border-slate-200 overflow-hidden">
        {/* ── Header bar ── */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-slate-50">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Pre-Test Symptom Check
          </p>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 text-lg leading-none transition"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="p-6 sm:p-8">
          {/* Icon */}
          <div className="flex justify-center mb-5">
            <span className="text-5xl">❓</span>
          </div>

          {/* Question */}
          <p className="text-lg font-semibold text-slate-800 mb-2 text-center">
            Check if CBC Test is Needed?
          </p>
          <p className="text-sm text-slate-600 text-center mb-8">
            Answer a few quick questions about the patient's symptoms and health profile. This assessment will help determine if a Complete Blood Count (CBC) test should be ordered.
          </p>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-5 py-3 rounded-xl border-2 border-slate-200 hover:border-slate-400
                         text-slate-700 font-semibold text-sm transition hover:bg-slate-50"
            >
              Not Now
            </button>
            <button
              onClick={handleStartInterview}
              className="flex-1 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700
                         text-white font-semibold text-sm transition shadow-sm"
            >
              Start Assessment →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // RESULT STAGE
  // ══════════════════════════════════════════════════════════════════════════
  if (stage === 'result' && result) {
    const needsTest = result.needs_test;
    return (
      <div className={`rounded-2xl border-2 p-6 shadow-md
        ${needsTest ? 'bg-orange-50 border-orange-400' : 'bg-green-50 border-green-400'}`}>

        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Triage Result</p>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full
            ${needsTest ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
            Random Forest Model
          </span>
        </div>

        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{needsTest ? '🩸' : '✅'}</span>
          <p className={`text-2xl font-extrabold tracking-tight
            ${needsTest ? 'text-orange-600' : 'text-green-600'}`}>
            {needsTest ? 'CBC Test Recommended' : 'No CBC Test Required'}
          </p>
        </div>

        <p className={`text-sm mb-5 ${needsTest ? 'text-orange-700' : 'text-green-700'}`}>
          {needsTest
            ? "Based on the patient's symptom profile, the ML model recommends ordering a Complete Blood Count test to screen for anemia."
            : "Based on the patient's symptom profile, the ML model does not indicate a need for a CBC test at this time."}
        </p>

        <button
          onClick={handleNewAssessment}
          className="w-full border border-slate-300 hover:border-slate-400 text-slate-600 hover:text-slate-800 font-medium py-2 rounded-xl text-sm transition"
        >
          ↩ Start New Assessment
        </button>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // INTERVIEW STAGE — one question at a time
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div className="bg-white rounded-2xl shadow-md border border-slate-200 overflow-hidden">

      {/* ── Header bar ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-slate-50">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Pre-Test Symptom Check
        </p>
        <button
          onClick={handleClose}
          className="text-slate-400 hover:text-slate-600 text-lg leading-none transition"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* ── Progress bar ── */}
      <div className="h-1 bg-slate-100">
        <div
          className="h-1 bg-blue-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="p-6 sm:p-8">
        {/* Question counter */}
        <p className="text-xs text-slate-400 mb-3">
          Question {qIndex + 1} of {TOTAL}
        </p>

        {/* Question text */}
        <p className="text-lg font-semibold text-slate-800 mb-6 leading-snug">
          {current.question}
        </p>

        {/* ── Choice question ── */}
        {current.type === 'choice' && (
          <div className="flex flex-col gap-3">
            {current.options.map(opt => (
              <button
                key={opt.label}
                onClick={() => recordAndAdvance(opt.value)}
                disabled={loading}
                className="w-full text-left px-5 py-3.5 rounded-xl border-2 border-slate-200
                           hover:border-blue-400 hover:bg-blue-50 text-slate-700 font-medium
                           text-sm transition disabled:opacity-50"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {/* ── Number input (Age) ── */}
        {current.type === 'number' && (
          <div className="space-y-3">
            <input
              type="number"
              min="1"
              max="120"
              placeholder={current.hint}
              value={ageInput}
              onChange={e => setAgeInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAgeNext()}
              autoFocus
              className="w-full rounded-xl border-2 border-slate-200 focus:border-blue-400
                         bg-slate-50 px-4 py-3 text-slate-800 text-sm focus:outline-none transition"
            />
            <button
              onClick={handleAgeNext}
              disabled={!ageInput || isNaN(parseInt(ageInput, 10))}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-200 disabled:cursor-not-allowed
                         text-white font-semibold py-3 rounded-xl transition text-sm"
            >
              Next →
            </button>
          </div>
        )}

        {/* ── Loading spinner (shown after last answer) ── */}
        {loading && (
          <div className="flex items-center justify-center gap-2 mt-6 text-slate-400 text-sm">
            <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Analysing with ML model…
          </div>
        )}

        {/* ── API error ── */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-300 text-red-600 rounded-lg px-4 py-3 text-sm flex items-center gap-2">
            <span>⚠️</span> {error}
            <button onClick={() => submitToAPI(answers)} className="ml-auto underline text-xs">Retry</button>
          </div>
        )}

        {/* ── Back button (not on first question) ── */}
        {qIndex > 0 && !loading && (
          <button
            onClick={() => setQIndex(i => i - 1)}
            className="mt-5 text-xs text-slate-400 hover:text-slate-600 transition"
          >
            ← Back
          </button>
        )}
      </div>
    </div>
  );
}
