/**
 * SocketContext.jsx
 * Global WebSocket context — single connection per session.
 * Maintains badge counts and dispatches events to page-level listeners.
 */

import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

const SocketContext = createContext(null);

export function SocketProvider({ children, user }) {
  const socketRef = useRef(null);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [pendingAppointments, setPendingAppointments] = useState(0);
  const [activeAlerts, setActiveAlerts] = useState(0);
  const listenersRef = useRef({});

  useEffect(() => {
    if (!user) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    // Single socket connection for entire session
    const socket = io(import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000', {
      query: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('join_personal_room', {
        username: user.username,
        role: user.role,
      });
    });

    // ── Global listeners — always active, update badge counts ──
    socket.on('new_message', (data) => {
      setUnreadMessages((prev) => prev + 1);
      triggerListeners('new_message', data);
    });

    socket.on('new_appointment', (data) => {
      setPendingAppointments((prev) => prev + 1);
      triggerListeners('new_appointment', data);
    });

    socket.on('appointment_confirmed', (data) => {
      triggerListeners('appointment_confirmed', data);
    });

    socket.on('appointment_cancelled', (data) => {
      setPendingAppointments((prev) => Math.max(0, prev - 1));
      triggerListeners('appointment_cancelled', data);
    });

    socket.on('critical_alert', (data) => {
      setActiveAlerts((prev) => prev + 1);
      triggerListeners('critical_alert', data);
    });

    socket.on('patient_alert', (data) => {
      setActiveAlerts((prev) => prev + 1);
      triggerListeners('patient_alert', data);
    });

    socket.on('my_alert', (data) => {
      triggerListeners('my_alert', data);
    });

    socket.on('new_report', (data) => {
      triggerListeners('new_report', data);
    });

    socket.on('new_prescription', (data) => {
      triggerListeners('new_prescription', data);
    });

    socket.on('medication_reminder', (data) => {
      if (window.Notification?.permission === 'granted') {
        new Notification('Medication Reminder', { body: data.message || 'Time to take your medication' });
      }
      triggerListeners('medication_reminder', data);
    });

    socket.on('assignment_update', (data) => {
      triggerListeners('assignment_update', data);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [user]);

  function triggerListeners(event, data) {
    const handlers = listenersRef.current[event] || [];
    handlers.forEach((fn) => fn(data));
  }

  const addListener = useCallback((event, handler) => {
    if (!listenersRef.current[event]) listenersRef.current[event] = [];
    listenersRef.current[event].push(handler);
  }, []);

  const removeListener = useCallback((event, handler) => {
    listenersRef.current[event] = (listenersRef.current[event] || []).filter(
      (fn) => fn !== handler
    );
  }, []);

  const clearBadge = useCallback((type) => {
    if (type === 'messages') setUnreadMessages(0);
    if (type === 'appointments') setPendingAppointments(0);
    if (type === 'alerts') setActiveAlerts(0);
  }, []);

  return (
    <SocketContext.Provider
      value={{
        socket: socketRef.current,
        unreadMessages,
        pendingAppointments,
        activeAlerts,
        addListener,
        removeListener,
        clearBadge,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  return useContext(SocketContext);
}
