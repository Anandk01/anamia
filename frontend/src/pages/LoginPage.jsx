/**
 * LoginPage.jsx
 * Split layout: dark left panel + white right panel with login form.
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';

// ─── Animated SVG Waveform ────────────────────────────────────────────────────
function AnimatedWaveform() {
  return (
    <svg
      viewBox="0 0 400 80"
      className="w-full opacity-30"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M0,40 C50,10 100,70 150,40 C200,10 250,70 300,40 C350,10 400,70 400,40"
        fill="none"
        stroke="#6366f1"
        strokeWidth="2"
        strokeLinecap="round"
      >
        <animate
          attributeName="d"
          dur="3s"
          repeatCount="indefinite"
          values="
            M0,40 C50,10 100,70 150,40 C200,10 250,70 300,40 C350,10 400,70 400,40;
            M0,40 C50,70 100,10 150,40 C200,70 250,10 300,40 C350,70 400,10 400,40;
            M0,40 C50,10 100,70 150,40 C200,10 250,70 300,40 C350,10 400,70 400,40
          "
        />
      </path>
      <path
        d="M0,40 C50,25 100,55 150,40 C200,25 250,55 300,40 C350,25 400,55 400,40"
        fill="none"
        stroke="#818cf8"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.6"
      >
        <animate
          attributeName="d"
          dur="4s"
          repeatCount="indefinite"
          values="
            M0,40 C50,25 100,55 150,40 C200,25 250,55 300,40 C350,25 400,55 400,40;
            M0,40 C50,55 100,25 150,40 C200,55 250,25 300,40 C350,55 400,25 400,40;
            M0,40 C50,25 100,55 150,40 C200,25 250,55 300,40 C350,25 400,55 400,40
          "
        />
      </path>
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login, isAuthenticated, getRole } = useAuth();

  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const usernameRef = useRef(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated()) {
      const role = getRole();
      if (role === 'admin') navigate('/admin', { replace: true });
      else if (role === 'doctor') navigate('/doctor', { replace: true });
      else navigate('/patient', { replace: true });
    }
    usernameRef.current?.focus();
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await client.post('/auth/login', {
        username: form.username,
        password: form.password,
      });
      const { token, user } = res.data;
      login(token, user);
      const role = user?.role || 'patient';
      if (role === 'admin') navigate('/admin', { replace: true });
      else if (role === 'doctor') navigate('/doctor', { replace: true });
      else navigate('/patient', { replace: true });
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden" style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
      {/* ── Left dark panel (45%) ── */}
      <div
        className="flex flex-col justify-between px-12 py-16"
        style={{ width: '45%', backgroundColor: '#0f1117', flexShrink: 0 }}
      >
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-sm"
              style={{ backgroundColor: '#6366f1' }}
            >
              A
            </div>
            <span className="text-white font-semibold text-lg tracking-tight">AnemiaDetect</span>
          </div>

          <h1 className="text-4xl font-bold text-white leading-tight mb-4">
            Clinical CBC<br />Analysis
          </h1>
          <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
            AI-powered anemia detection using supervised machine learning on complete blood count parameters.
          </p>
        </div>

        <div className="space-y-6">
          <AnimatedWaveform />
          <div className="flex gap-6">
            {['RF Classifier', 'GB Severity', 'SHAP Explain'].map((label) => (
              <div key={label} className="text-center">
                <div className="w-2 h-2 rounded-full mx-auto mb-1" style={{ backgroundColor: '#6366f1' }} />
                <span className="text-slate-500 text-xs">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right white panel ── */}
      <div className="flex-1 bg-white flex items-center justify-center px-12">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-bold text-slate-800 mb-1">Welcome back</h2>
          <p className="text-slate-500 text-sm mb-8">Sign in to your account</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                {t('username')}
              </label>
              <input
                ref={usernameRef}
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="Enter username"
                required
                autoComplete="username"
                className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                style={{ '--tw-ring-color': '#6366f1' }}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                {t('password')}
              </label>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
                autoComplete="current-password"
                className="w-full rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 rounded px-3 py-2 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white font-semibold py-2.5 rounded text-sm transition disabled:opacity-60"
              style={{ backgroundColor: loading ? '#818cf8' : '#6366f1' }}
            >
              {loading ? t('loading') : t('login')}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 space-y-3 text-center text-sm">
            <p className="text-slate-500">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="font-medium" style={{ color: '#6366f1' }}>
                Register
              </Link>
            </p>
            <p>
              <Link to="/forgot-password" className="text-slate-400 hover:text-slate-600 transition text-xs">
                Forgot password?
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
