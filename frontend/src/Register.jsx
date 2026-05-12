import { useState } from 'react';

const INPUT_CLS = `w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm
  text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2
  focus:ring-blue-400 focus:border-transparent transition`;

export default function Register({ onRegisterSuccess, onSwitchToLogin }) {
  // Multi-step form states
  const [step, setStep] = useState('details'); // 'details' | 'otp' | 'success'
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    otp: '',
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  function handleChange(e) {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  // Step 1: Submit details and request OTP
  async function handleRequestOTP(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validation
    if (!formData.email.trim()) {
      setError('Email is required');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address');
      return;
    }
    if (!formData.username.trim()) {
      setError('Username is required');
      return;
    }
    if (formData.username.length < 3) {
      setError('Username must be at least 3 characters');
      return;
    }
    if (!formData.password) {
      setError('Password is required');
      return;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          username: formData.username,
          password: formData.password,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);
      
      setSuccess(`OTP sent to ${formData.email}. Check your inbox!`);
      setStep('otp');
      startResendCooldown();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Verify OTP and create account
  async function handleVerifyOTP(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!formData.otp.trim() || formData.otp.length !== 6) {
      setError('Please enter a valid 6-digit OTP');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/verify-register-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          otp: formData.otp,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);
      
      setSuccess('✅ Account created successfully! Redirecting to login...');
      setStep('success');
      setTimeout(() => {
        onSwitchToLogin();
      }, 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Resend OTP handler
  async function handleResendOTP() {
    setError(null);
    setSuccess(null);
    setLoading(true);
    
    try {
      const response = await fetch('http://127.0.0.1:5000/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          username: formData.username,
          password: formData.password,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);
      
      setSuccess('OTP resent! Check your email.');
      startResendCooldown();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function startResendCooldown() {
    setResendCooldown(30);
    const interval = setInterval(() => {
      setResendCooldown(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function goBack() {
    setStep('details');
    setFormData(prev => ({ ...prev, otp: '' }));
    setError(null);
    setSuccess(null);
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <span className="inline-block bg-blue-100 text-blue-700 text-xs font-semibold tracking-widest uppercase px-3 py-1 rounded-full mb-4">
            ML-Powered Diagnostic Tool
          </span>
          <h1 className="text-3xl font-bold text-slate-800">Create Account</h1>
          <p className="text-slate-500 text-sm mt-1">Register to access the CBC dashboard</p>
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-slate-200 p-8">
          <h2 className="text-base font-semibold text-slate-700 mb-5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
            {step === 'details' && 'New Doctor Registration'}
            {step === 'otp' && 'Verify Email'}
            {step === 'success' && 'Success'}
          </h2>

          {/* STEP 1: REGISTRATION DETAILS */}
          {step === 'details' && (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="your.email@example.com"
                  required
                  autoFocus
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Username
                </label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Choose a username"
                  required
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Password
                </label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="At least 6 characters"
                  required
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Confirm your password"
                  required
                  className={INPUT_CLS}
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-300 text-red-600 rounded-lg px-4 py-3 text-sm flex items-center gap-2">
                  <span>⚠️</span> {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-2.5 rounded-xl transition text-sm tracking-wide shadow-sm"
              >
                {loading ? 'Sending OTP…' : 'Continue & Send OTP'}
              </button>
            </form>
          )}

          {/* STEP 2: OTP VERIFICATION */}
          {step === 'otp' && (
            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-700">
                <p className="font-medium">📧 Verification Code Sent</p>
                <p className="text-xs mt-1 text-blue-600">Check your email at <span className="font-semibold">{formData.email}</span></p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Verification Code (6 digits)
                </label>
                <input
                  type="text"
                  name="otp"
                  value={formData.otp}
                  onChange={handleChange}
                  placeholder="000000"
                  maxLength="6"
                  required
                  autoFocus
                  className={INPUT_CLS + ' text-center text-lg tracking-widest font-mono'}
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-300 text-red-600 rounded-lg px-4 py-3 text-sm flex items-center gap-2">
                  <span>⚠️</span> {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-2.5 rounded-xl transition text-sm tracking-wide shadow-sm"
              >
                {loading ? 'Verifying…' : 'Verify & Create Account'}
              </button>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={resendCooldown > 0 || loading}
                  className="text-xs text-blue-600 hover:text-blue-700 disabled:text-slate-400 font-medium"
                >
                  {resendCooldown > 0 ? `Resend OTP in ${resendCooldown}s` : 'Didn\'t receive it? Resend OTP'}
                </button>
              </div>

              <button
                type="button"
                onClick={goBack}
                className="w-full text-slate-600 hover:text-slate-800 border border-slate-300 px-4 py-2 rounded-lg transition font-medium text-sm"
              >
                Back to Details
              </button>
            </form>
          )}

          {/* STEP 3: SUCCESS */}
          {step === 'success' && (
            <div className="text-center space-y-4">
              <div className="text-5xl">✅</div>
              <p className="text-slate-700 font-semibold">Account Created Successfully!</p>
              <p className="text-slate-500 text-sm">You can now log in with your credentials.</p>
            </div>
          )}

          {step !== 'success' && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-center text-xs text-slate-500">
                Already have an account?{' '}
                <button
                  onClick={onSwitchToLogin}
                  className="text-blue-600 hover:text-blue-700 font-semibold"
                >
                  Sign in here
                </button>
              </p>
            </div>
          )}
        </div>

     
      </div>
    </div>
  );
}
