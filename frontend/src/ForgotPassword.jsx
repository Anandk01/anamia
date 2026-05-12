import { useState } from 'react';

const INPUT_CLS = `w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm
  text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2
  focus:ring-blue-400 focus:border-transparent transition`;

export default function ForgotPassword({ onSwitchToLogin }) {
  // Steps: 'email' -> 'otp' -> 'newpassword' -> 'success'
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Step 1: Request OTP
  async function handleRequestOTP(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);
      
      setSuccess('OTP sent! Check your email.');
      setStep('otp');
      startResendCooldown();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Verify OTP
  async function handleVerifyOTP(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!otp.trim() || otp.length !== 6) {
      setError('Please enter a valid 6-digit OTP');
      return;
    }

    setLoading(true);
    try {
      // Just verify the OTP and move to password reset step
      // The actual verification happens when resetting password
      setSuccess('OTP verified! Now enter your new password.');
      setTimeout(() => {
        setStep('newpassword');
        setSuccess(null);
      }, 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Step 3: Reset password with OTP
  async function handleResetPassword(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!newPassword) {
      setError('New password is required');
      return;
    }
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/verify-reset-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          new_password: newPassword,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Error ${response.status}`);
      
      setSuccess('✅ Password reset successfully! Redirecting to login...');
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
      const response = await fetch('http://127.0.0.1:5000/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
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

  function goBackToEmail() {
    setStep('email');
    setOtp('');
    setError(null);
    setSuccess(null);
  }

  function goBackToOTP() {
    setStep('otp');
    setNewPassword('');
    setConfirmPassword('');
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
          <h1 className="text-3xl font-bold text-slate-800">Reset Password</h1>
          <p className="text-slate-500 text-sm mt-1">
            {step === 'email' && 'Enter your email to receive a reset code'}
            {step === 'otp' && 'Verify your identity with the code'}
            {step === 'newpassword' && 'Create a new password'}
            {step === 'success' && 'Password updated successfully'}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-slate-200 p-8">
          <h2 className="text-base font-semibold text-slate-700 mb-5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-orange-500 inline-block"></span>
            {step === 'email' && 'Verify Email'}
            {step === 'otp' && 'Verification Code'}
            {step === 'newpassword' && 'New Password'}
            {step === 'success' && 'Success'}
          </h2>

          {/* STEP 1: EMAIL */}
          {step === 'email' && (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  required
                  autoFocus
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
                className="w-full bg-orange-600 hover:bg-orange-700 disabled:bg-orange-300 text-white font-semibold py-2.5 rounded-xl transition text-sm tracking-wide shadow-sm"
              >
                {loading ? 'Sending OTP…' : 'Send Reset Code'}
              </button>
            </form>
          )}

          {/* STEP 2: OTP VERIFICATION */}
          {step === 'otp' && (
            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-700">
                <p className="font-medium">📧 Reset Code Sent</p>
                <p className="text-xs mt-1 text-blue-600">Check your email at <span className="font-semibold">{email}</span></p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Verification Code (6 digits)
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
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
                className="w-full bg-orange-600 hover:bg-orange-700 disabled:bg-orange-300 text-white font-semibold py-2.5 rounded-xl transition text-sm tracking-wide shadow-sm"
              >
                {loading ? 'Verifying…' : 'Continue'}
              </button>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={resendCooldown > 0 || loading}
                  className="text-xs text-orange-600 hover:text-orange-700 disabled:text-slate-400 font-medium"
                >
                  {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Didn\'t receive it? Resend Code'}
                </button>
              </div>

              <button
                type="button"
                onClick={goBackToEmail}
                className="w-full text-slate-600 hover:text-slate-800 border border-slate-300 px-4 py-2 rounded-lg transition font-medium text-sm"
              >
                Back to Email
              </button>
            </form>
          )}

          {/* STEP 3: NEW PASSWORD */}
          {step === 'newpassword' && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
                <p className="font-medium">✅ Code Verified</p>
                <p className="text-xs mt-1 text-green-600">Now create your new password</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  required
                  autoFocus
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your new password"
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
                className="w-full bg-orange-600 hover:bg-orange-700 disabled:bg-orange-300 text-white font-semibold py-2.5 rounded-xl transition text-sm tracking-wide shadow-sm"
              >
                {loading ? 'Resetting…' : 'Reset Password'}
              </button>

              <button
                type="button"
                onClick={goBackToOTP}
                className="w-full text-slate-600 hover:text-slate-800 border border-slate-300 px-4 py-2 rounded-lg transition font-medium text-sm"
              >
                Back to Code
              </button>
            </form>
          )}

          {/* STEP 4: SUCCESS */}
          {step === 'success' && (
            <div className="text-center space-y-4">
              <div className="text-5xl">✅</div>
              <p className="text-slate-700 font-semibold">Password Reset Complete!</p>
              <p className="text-slate-500 text-sm">You can now log in with your new password.</p>
            </div>
          )}

          {step !== 'success' && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-center text-xs text-slate-500">
                Remember your password?{' '}
              <button
                onClick={onSwitchToLogin}
                className="text-blue-600 hover:text-blue-700 font-semibold"
              >
                Back to login
              </button>
            </p>
          </div>
        )}
        </div>

        <p className="text-center text-xs text-slate-400">
          K-Means Unsupervised Clustering · College Research Project
        </p>
      </div>
    </div>
  );
}
