/**
 * LoginPage.jsx
 * Modern glass-morphism login with animated gradient background
 * and floating medical-themed decorations.
 */

import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth.js';
import client from '../api/client.js';

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
    <div
      className="relative min-h-screen w-full flex items-center justify-center overflow-hidden px-4"
      style={{
        background: 'linear-gradient(-45deg, #1e1b4b, #4c1d95, #312e81, #1e3a5f, #2e1065)',
        backgroundSize: '400% 400%',
        animation: 'gradient-shift 15s ease infinite',
      }}
    >
      {/* ── Floating background shapes (blood cells / DNA) ── */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
        {/* Large blood cell */}
        <div
          className="absolute rounded-full border-4 border-red-400/20"
          style={{
            width: '120px',
            height: '120px',
            top: '10%',
            left: '8%',
            animation: 'float 6s ease-in-out infinite',
            background: 'radial-gradient(circle at 40% 40%, rgba(239,68,68,0.15), transparent 70%)',
          }}
        />
        {/* Small blood cell */}
        <div
          className="absolute rounded-full border-2 border-red-300/20"
          style={{
            width: '60px',
            height: '60px',
            top: '70%',
            left: '12%',
            animation: 'float 8s ease-in-out infinite 1s',
            background: 'radial-gradient(circle at 40% 40%, rgba(239,68,68,0.1), transparent 70%)',
          }}
        />
        {/* DNA helix shape - top right */}
        <div
          className="absolute"
          style={{
            width: '80px',
            height: '200px',
            top: '5%',
            right: '10%',
            animation: 'float 7s ease-in-out infinite 0.5s',
          }}
        >
          <div className="w-full h-full relative">
            <div className="absolute inset-0 rounded-full border-2 border-purple-300/20" style={{ transform: 'rotateX(60deg) rotateZ(20deg)' }} />
            <div className="absolute inset-2 rounded-full border-2 border-indigo-300/15" style={{ transform: 'rotateX(60deg) rotateZ(-20deg)' }} />
          </div>
        </div>
        {/* Pulsing circle - bottom right */}
        <div
          className="absolute rounded-full"
          style={{
            width: '180px',
            height: '180px',
            bottom: '15%',
            right: '8%',
            animation: 'pulse-slow 4s ease-in-out infinite',
            background: 'radial-gradient(circle, rgba(129,140,248,0.2), transparent 70%)',
          }}
        />
        {/* Small floating dot */}
        <div
          className="absolute rounded-full bg-purple-400/20"
          style={{
            width: '30px',
            height: '30px',
            top: '45%',
            left: '5%',
            animation: 'pulse-slow 5s ease-in-out infinite 2s',
          }}
        />
        {/* Medium blood cell - right side */}
        <div
          className="absolute rounded-full border-3 border-rose-400/15"
          style={{
            width: '90px',
            height: '90px',
            top: '35%',
            right: '5%',
            animation: 'float 9s ease-in-out infinite 2s',
            background: 'radial-gradient(circle at 50% 50%, rgba(244,63,94,0.1), transparent 70%)',
          }}
        />
        {/* DNA dot chain - left side */}
        <div className="absolute" style={{ top: '30%', left: '20%', animation: 'float 10s ease-in-out infinite 3s' }}>
          <div className="flex flex-col gap-3">
            <div className="w-3 h-3 rounded-full bg-indigo-400/20" />
            <div className="w-2 h-2 rounded-full bg-purple-400/25 ml-2" />
            <div className="w-3 h-3 rounded-full bg-indigo-400/20" />
            <div className="w-2 h-2 rounded-full bg-purple-400/25 ml-2" />
            <div className="w-3 h-3 rounded-full bg-indigo-400/20" />
          </div>
        </div>
        {/* Large subtle glow - center */}
        <div
          className="absolute rounded-full"
          style={{
            width: '400px',
            height: '400px',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'radial-gradient(circle, rgba(99,102,241,0.08), transparent 70%)',
          }}
        />
      </div>

      {/* ── Main content ── */}
      <div className="relative z-10 w-full max-w-md flex flex-col items-center">
        {/* Logo and tagline */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center shadow-lg shadow-red-500/30">
              <span className="text-2xl" role="img" aria-label="blood drop">🩸</span>
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              AnemiaCare
            </h1>
          </div>
          <p className="text-indigo-200/80 text-sm font-medium">
            AI-Powered Anemia Detection Platform
          </p>
        </div>

        {/* Glass-morphism card */}
        <div
          className="w-full rounded-2xl p-8 shadow-2xl border border-white/10"
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
          }}
        >
          <div className="text-center mb-6">
            <h2 className="text-xl font-semibold text-white mb-1">Welcome Back</h2>
            <p className="text-indigo-200/60 text-sm">Sign in to continue your session</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-medium text-indigo-200/70 uppercase tracking-wider mb-2">
                {t('username')}
              </label>
              <input
                ref={usernameRef}
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="Enter your username"
                required
                autoComplete="username"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-indigo-300/40 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 focus:border-indigo-400/30 focus:bg-white/10 transition-all duration-300"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-indigo-200/70 uppercase tracking-wider mb-2">
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
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-indigo-300/40 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 focus:border-indigo-400/30 focus:bg-white/10 transition-all duration-300"
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-400/30 text-red-300 rounded-xl px-4 py-3 text-sm backdrop-blur-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white font-semibold py-3 rounded-xl text-sm transition-all duration-300 disabled:opacity-60 hover:shadow-lg hover:shadow-indigo-500/30 hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: loading
                  ? 'linear-gradient(135deg, #818cf8, #6366f1)'
                  : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              }}
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t('loading')}
                </span>
              ) : (
                t('login')
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/10 space-y-3 text-center text-sm">
            <p className="text-indigo-200/60">
              Don&apos;t have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-indigo-300 hover:text-white transition-colors duration-200"
              >
                Register
              </Link>
            </p>
            <p>
              <Link
                to="/forgot-password"
                className="text-indigo-300/50 hover:text-indigo-200 transition-colors duration-200 text-xs"
              >
                Forgot password?
              </Link>
            </p>
          </div>
        </div>

        {/* Feature badges */}
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
            <span className="text-base" role="img" aria-label="AI">🧬</span>
            <span className="text-xs font-medium text-indigo-200/80">AI-Powered</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
            <span className="text-base" role="img" aria-label="secure">🔒</span>
            <span className="text-xs font-medium text-indigo-200/80">Secure</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
            <span className="text-base" role="img" aria-label="multi-role">👥</span>
            <span className="text-xs font-medium text-indigo-200/80">Multi-Role</span>
          </div>
        </div>
      </div>
    </div>
  );
}
