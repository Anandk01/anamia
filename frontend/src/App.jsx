/**
 * App.jsx
 * React Router v6 app with role-based PrivateRoute.
 * Routes: /login, /register, /forgot-password, /patient/*, /doctor/*, /admin/*
 */

import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth.js';
import { SocketProvider } from './contexts/SocketContext.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx';
import PatientDashboard from './pages/PatientDashboard.jsx';
import DoctorDashboard from './pages/DoctorDashboard.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';

// ─── PrivateRoute ─────────────────────────────────────────────────────────────
function PrivateRoute({ children, allowedRoles }) {
  const { isAuthenticated, getRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const role = getRole();
  if (allowedRoles && !allowedRoles.includes(role)) {
    // Redirect to the correct dashboard for the user's actual role
    if (role === 'admin') return <Navigate to="/admin" replace />;
    if (role === 'doctor') return <Navigate to="/doctor" replace />;
    return <Navigate to="/patient" replace />;
  }

  return children;
}

// ─── RoleRedirect — sends authenticated users to their dashboard ──────────────
function RoleRedirect() {
  const { isAuthenticated, getRole } = useAuth();
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (role === 'admin') return <Navigate to="/admin" replace />;
  if (role === 'doctor') return <Navigate to="/doctor" replace />;
  return <Navigate to="/patient" replace />;
}

export default function App() {
  const { getUser, isAuthenticated } = useAuth();
  const [user, setUser] = useState(() => (isAuthenticated() ? getUser() : null));

  // Re-check user on storage changes (login/logout in another tab)
  useEffect(() => {
    const onStorage = () => setUser(isAuthenticated() ? getUser() : null);
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return (
    <SocketProvider user={user}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />

          {/* Role-based protected routes */}
          <Route
            path="/patient/*"
            element={
              <PrivateRoute allowedRoles={['patient']}>
                <PatientDashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/doctor/*"
            element={
              <PrivateRoute allowedRoles={['doctor']}>
                <DoctorDashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/admin/*"
            element={
              <PrivateRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </PrivateRoute>
            }
          />

          {/* Root redirect */}
          <Route path="/" element={<RoleRedirect />} />
          <Route path="*" element={<RoleRedirect />} />
        </Routes>
      </BrowserRouter>
    </SocketProvider>
  );
}
