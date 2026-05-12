import client from '../api/client';

function decodeJWT(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function useAuth() {
  function login(token, user) {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
  }

  function logout() {
    const token = localStorage.getItem('token');
    if (token) {
      client.post('/auth/logout').catch(() => {});
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  function getRole() {
    const token = localStorage.getItem('token');
    if (!token) return null;
    const payload = decodeJWT(token);
    return payload?.role || null;
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem('user')) || null;
    } catch {
      return null;
    }
  }

  function isAuthenticated() {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = decodeJWT(token);
    if (!payload) return false;
    return payload.exp * 1000 > Date.now();
  }

  return { login, logout, getRole, getUser, isAuthenticated };
}
