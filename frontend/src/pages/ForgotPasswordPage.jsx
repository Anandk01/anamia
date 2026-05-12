/**
 * ForgotPasswordPage.jsx
 * 3-step flow: Email → OTP → New Password with animated progress bar.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client.js';

// ─── Animated progress bar ────────────────────────────────────────────────────
function ProgressBar({ step }) {
  const pct = ((step - 1) / 2) * 100;
  return (
    <div className="mb-8">
      <div className="flex justify-between text-xs text-slate-400 mb-2">
        <span className={step >= 1 ? 'font-semibold' : ''} style={{ color: step >= 1 ? '#6366f1' : undefined }}>Email</span>
        <span className={step >= 2 ? 'font-semibold' : ''} style={{ color: step >= 2 ? '#6366f1' : undefined }}>OTP</span>
        <span className={step >= 3 ? 'font-semibold' : ''} style={{ color: step >= 3 ? '#6366f1' : undefined }}>New Password</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: '#6366f1' }}
        />
      </div>
    </div>
  );
}

export default function ForgotPasswordPage() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  async function handleEmailSubmit(e) {
    e.preventDefault();
    if (!email.trim()) { setError('Email is required.'); return; }
    setLoading(true);
    setError(null);
    try {
      await client.post('/auth/forgot-password', { email });
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to send OTP.');
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpSubmit(e) {
    e.preventDefault();
    if (otp.length < 6) { setError('Enter the 6-digit OTP.'); return; }
    setLoading(true);
    setError(null);
    try {
      await client.post('/auth/verify-reset-otp', { email, otp });
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.message || 'Invalid OTP.');
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    if (!newPassword || newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }
    setLoading(true);
    setError(null);
    try {
      await client.post('/auth/reset-password', { email, otp, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reset password.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* Left dark panel */}
      <div className="flex flex-col justify-between px-12 py-16" style={{ width: '45%', backgroundColor: '#0f1117', flexShrink: 0 }}>
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-sm" style={{ backgroundColor: '#6366f1' }}>A</div>
            <span className="text-white font-semibold text-lg tracking-tight">AnemiaDetect</span>
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">Reset your<br />password</h1>
          <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
            We&apos;ll send a one-time code to your email to verify your identity.
          </p>
        </div>
        <div className="space-y-3">
          {['Step 1: Enter your email', 'Step 2: Verify OTP code', 'Step 3: Set new password'].map((s, i) => (
            <div key={s} className="flex items-center gap-3">
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                style={{ backgroundColor: step > i ? '#6366f1' : '#1e2130', color: step > i ? '#fff' : '#4b5563', border: '1px solid', borderColor: step > i ? '#6366f1' : '#374151' }}
              >
                {i + 1}
              </div>
              <span className="text-slate-400 text-sm">{s}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right white panel */}
      <div className="flex-1 bg-white flex items-center justify-center px-12">
        <div className="w-full max-w-sm">
          <ProgressBar step={step} />

          {success ? (
            <div className="text-center space-y-4">
              <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto" style={{ backgroundColor: '#d1fae5' }}>
                <span className="text-2xl">✓</span>
              </div>
              <h2 className="text-xl font-bold text-slate-800">Password Reset!</h2>
              <p className="text-slate-500 text-sm">Your password has been updated successfully.</p>
              <Link to="/login" className="block w-full text-center text-white font-semibold py-2.5 rounded text-sm transition" style={{ backgroundColor: '#6366f1' }}>
                Back to Login
              </Link>
            </div>
          ) : step === 1 ? (
            <>
              <h2 className="text-2xl font-bold text-slate-800 mb-1">Forgot Password</h2>
              <p className="text-slate-500 text-sm mb-6">Enter your registered email address</p>
              <form onSubmit={handleEmailSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                    className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                  />
                </div>
                {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
                <button type="submit" disabled={loading} className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60" style={{ backgroundColor: '#6366f1' }}>
                  {loading ? 'Sending...' : 'Send OTP'}
                </button>
              </form>
            </>
          ) : step === 2 ? (
            <>
              <h2 className="text-2xl font-bold text-slate-800 mb-1">Enter OTP</h2>
              <p className="text-slate-500 text-sm mb-6">Check your email for the 6-digit code</p>
              <form onSubmit={handleOtpSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">OTP Code</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    autoFocus
                    className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition text-center tracking-widest text-lg font-bold"
                  />
                </div>
                {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
                <button type="submit" disabled={loading || otp.length < 6} className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60" style={{ backgroundColor: '#6366f1' }}>
                  {loading ? 'Verifying...' : 'Verify OTP'}
                </button>
                <button type="button" onClick={() => setStep(1)} className="w-full text-slate-500 text-sm hover:text-slate-700 transition">← Back</button>
              </form>
            </>
          ) : (
            <>
              <h2 className="text-2xl font-bold text-slate-800 mb-1">New Password</h2>
              <p className="text-slate-500 text-sm mb-6">Choose a strong password for your account</p>
              <form onSubmit={handlePasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min 8 characters"
                    autoFocus
                    className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Confirm Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                    className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                  />
                </div>
                {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">{error}</div>}
                <button type="submit" disabled={loading} className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60" style={{ backgroundColor: '#6366f1' }}>
                  {loading ? 'Resetting...' : 'Reset Password'}
                </button>
              </form>
            </>
          )}

          <p className="mt-6 text-center text-sm text-slate-500">
            <Link to="/login" className="font-medium" style={{ color: '#6366f1' }}>← Back to Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
