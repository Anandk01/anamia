/**
 * RegisterPage.jsx
 * 2-step registration: Step 1 (fields) → Step 2 (OTP).
 * Same split layout as LoginPage.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import client from '../api/client.js';
import { useAuth } from '../hooks/useAuth.js';

// ─── Step indicator ───────────────────────────────────────────────────────────
function StepIndicator({ step }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {[1, 2].map((s) => (
        <div key={s} className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all"
            style={{
              backgroundColor: step >= s ? '#6366f1' : '#e2e8f0',
              color: step >= s ? '#fff' : '#94a3b8',
            }}
          >
            {s}
          </div>
          {s < 2 && (
            <div
              className="w-8 h-0.5 transition-all"
              style={{ backgroundColor: step > s ? '#6366f1' : '#e2e8f0' }}
            />
          )}
        </div>
      ))}
      <span className="ml-2 text-xs text-slate-500">
        {step === 1 ? 'Account Details' : 'Verify Email'}
      </span>
    </div>
  );
}

// ─── OTP Input (6 separate digit boxes) ──────────────────────────────────────
function OtpInput({ value, onChange }) {
  const refs = Array.from({ length: 6 }, () => useRef(null));

  function handleDigitChange(idx, e) {
    const digit = e.target.value.replace(/\D/g, '').slice(-1);
    const arr = value.split('');
    arr[idx] = digit;
    const next = arr.join('');
    onChange(next);
    if (digit && idx < 5) refs[idx + 1].current?.focus();
  }

  function handleKeyDown(idx, e) {
    if (e.key === 'Backspace' && !value[idx] && idx > 0) {
      refs[idx - 1].current?.focus();
    }
  }

  function handlePaste(e) {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    onChange(pasted.padEnd(6, '').slice(0, 6));
    refs[Math.min(pasted.length, 5)].current?.focus();
    e.preventDefault();
  }

  return (
    <div className="flex gap-2">
      {Array.from({ length: 6 }).map((_, idx) => (
        <input
          key={idx}
          ref={refs[idx]}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[idx] || ''}
          onChange={(e) => handleDigitChange(idx, e)}
          onKeyDown={(e) => handleKeyDown(idx, e)}
          onPaste={handlePaste}
          className="w-10 h-12 text-center text-lg font-bold rounded border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 transition"
          style={{ '--tw-ring-color': '#6366f1' }}
        />
      ))}
    </div>
  );
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState(null);

  function validate() {
    const errs = {};
    if (!form.username.trim()) errs.username = 'Username is required';
    else if (form.username.length < 3) errs.username = 'Min 3 characters';
    if (!form.email.trim()) errs.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errs.email = 'Invalid email';
    if (!form.password) errs.password = 'Password is required';
    else if (form.password.length < 8) errs.password = 'Min 8 characters';
    return errs;
  }

  async function handleStep1(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    setServerError(null);
    try {
      await client.post('/auth/register', form);
      setStep(2);
    } catch (err) {
      setServerError(err.response?.data?.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleStep2(e) {
    e.preventDefault();
    if (otp.length < 6) { setServerError('Please enter the 6-digit OTP.'); return; }
    setLoading(true);
    setServerError(null);
    try {
      const res = await client.post('/auth/verify-register-otp', {
        email: form.email,
        otp,
      });
      const { token, user } = res.data;
      if (token) login(token, user);
      navigate('/patient', { replace: true });
    } catch (err) {
      setServerError(err.response?.data?.message || 'OTP verification failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Left dark panel */}
      <div
        className="flex flex-col justify-between px-12 py-16"
        style={{ width: '45%', backgroundColor: '#0f1117', flexShrink: 0 }}
      >
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-sm" style={{ backgroundColor: '#6366f1' }}>A</div>
            <span className="text-white font-semibold text-lg tracking-tight">AnemiaDetect</span>
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">Create your<br />account</h1>
          <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
            Join the platform to track your CBC results and get AI-powered anemia insights.
          </p>
        </div>
        <div className="space-y-3">
          {['Secure OTP verification', 'Role-based access', 'Multilingual support'].map((f) => (
            <div key={f} className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#6366f1' }} />
              <span className="text-slate-400 text-sm">{f}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right white panel */}
      <div className="flex-1 bg-white flex items-center justify-center px-12">
        <div className="w-full max-w-sm">
          <StepIndicator step={step} />

          {step === 1 ? (
            <>
              <h2 className="text-2xl font-bold text-slate-800 mb-1">Account Details</h2>
              <p className="text-slate-500 text-sm mb-6">Fill in your information to get started</p>
              <form onSubmit={handleStep1} className="space-y-4">
                {[
                  { name: 'username', label: 'Username', type: 'text', placeholder: 'e.g. john_doe' },
                  { name: 'email', label: 'Email', type: 'email', placeholder: 'you@example.com' },
                  { name: 'password', label: 'Password', type: 'password', placeholder: '••••••••' },
                ].map(({ name, label, type, placeholder }) => (
                  <div key={name}>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">{label}</label>
                    <input
                      type={type}
                      name={name}
                      value={form[name]}
                      onChange={(e) => setForm((p) => ({ ...p, [name]: e.target.value }))}
                      placeholder={placeholder}
                      className={`w-full rounded border px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition ${errors[name] ? 'border-red-400 bg-red-50' : 'border-slate-200 bg-slate-50'}`}
                    />
                    {errors[name] && <p className="text-red-500 text-xs mt-1">{errors[name]}</p>}
                  </div>
                ))}
                {serverError && <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{serverError}</div>}
                <button type="submit" disabled={loading} className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60" style={{ backgroundColor: '#6366f1' }}>
                  {loading ? 'Sending OTP...' : 'Continue'}
                </button>
              </form>
            </>
          ) : (
            <>
              <h2 className="text-2xl font-bold text-slate-800 mb-1">Verify Email</h2>
              <p className="text-slate-500 text-sm mb-6">Enter the 6-digit code sent to <strong>{form.email}</strong></p>
              <form onSubmit={handleStep2} className="space-y-6">
                <OtpInput value={otp} onChange={setOtp} />
                {serverError && <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{serverError}</div>}
                <button type="submit" disabled={loading || otp.length < 6} className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60" style={{ backgroundColor: '#6366f1' }}>
                  {loading ? 'Verifying...' : 'Verify & Create Account'}
                </button>
                <button type="button" onClick={() => setStep(1)} className="w-full text-slate-500 text-sm hover:text-slate-700 transition">
                  ← Back
                </button>
              </form>
            </>
          )}

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="font-medium" style={{ color: '#6366f1' }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
