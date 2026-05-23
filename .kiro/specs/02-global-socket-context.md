# Spec: Global WebSocket Context (BUILD SECOND)

## Overview
This is the real-time infrastructure. Kiro generates socket listeners INSIDE individual
page components — which means events are missed when the user is on a different page.
This spec creates ONE global socket connection that lives for the entire session and
keeps badge counts and notifications updated regardless of which page is open.

## Requirements

### 1. Backend — app.py
Install and configure Flask-SocketIO:

```python
from flask_socketio import SocketIO, join_room, emit
socketio = SocketIO(app, cors_allowed_origins="*")
```

Add these socket event handlers:

```python
@socketio.on('connect')
def on_connect():
    # Verify JWT from auth header
    token = request.args.get('token')
    if not token: return False  # reject connection
    try:
        data = decode_jwt(token)
        request.user = data['username']
        request.role = data['role']
    except: return False

@socketio.on('join_personal_room')
def on_join(data):
    username = data['username']
    join_room(f"user_{username}")
    if data.get('role') == 'admin':
        join_room('admin_room')

@socketio.on('disconnect')
def on_disconnect():
    pass  # Flask-SocketIO handles room cleanup
```

Run with: `socketio.run(app)` instead of `app.run()`

### 2. Backend — emit helper (utils.py)
Add this function. Import and call it from every blueprint that needs real-time:

```python
from flask_socketio import emit
from app import socketio

def notify_user(username: str, event: str, data: dict):
    """Send a real-time event to a specific user's room"""
    socketio.emit(event, data, to=f"user_{username}")

def notify_admin(event: str, data: dict):
    """Send a real-time event to all admins"""
    socketio.emit(event, data, to='admin_room')
```

### 3. Frontend — SocketContext.jsx (NEW FILE in /frontend/src/context/)

```jsx
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

const SocketContext = createContext(null);

export function SocketProvider({ children, user }) {
  const socketRef = useRef(null);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [pendingAppointments, setPendingAppointments] = useState(0);
  const [activeAlerts, setActiveAlerts] = useState(0);
  const listenersRef = useRef({});

  useEffect(() => {
    if (!user) return;

    // ONE socket connection for entire session
    const socket = io(import.meta.env.VITE_BACKEND_URL, {
      query: { token: localStorage.getItem('token') }
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('join_personal_room', {
        username: user.username,
        role: user.role
      });
    });

    // GLOBAL listeners — always active, update badge counts
    socket.on('new_message', (data) => {
      setUnreadMessages(prev => prev + 1);
      triggerListeners('new_message', data);
    });

    socket.on('new_appointment', (data) => {
      setPendingAppointments(prev => prev + 1);
      triggerListeners('new_appointment', data);
    });

    socket.on('appointment_confirmed', (data) => {
      triggerListeners('appointment_confirmed', data);
    });

    socket.on('appointment_cancelled', (data) => {
      setPendingAppointments(prev => Math.max(0, prev - 1));
      triggerListeners('appointment_cancelled', data);
    });

    socket.on('critical_alert', (data) => {
      setActiveAlerts(prev => prev + 1);
      triggerListeners('critical_alert', data);
    });

    socket.on('patient_alert', (data) => {
      setActiveAlerts(prev => prev + 1);
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
      // Show browser notification or toast regardless of current page
      if (window.Notification?.permission === 'granted') {
        new Notification(`Medication Reminder`, { body: data.message });
      }
      triggerListeners('medication_reminder', data);
    });

    socket.on('assignment_update', (data) => {
      triggerListeners('assignment_update', data);
    });

    return () => socket.disconnect();
  }, [user]);

  function triggerListeners(event, data) {
    const handlers = listenersRef.current[event] || [];
    handlers.forEach(fn => fn(data));
  }

  // Page-level components call this to get event data when they're mounted
  function addListener(event, handler) {
    if (!listenersRef.current[event]) listenersRef.current[event] = [];
    listenersRef.current[event].push(handler);
  }

  function removeListener(event, handler) {
    listenersRef.current[event] = (listenersRef.current[event] || [])
      .filter(fn => fn !== handler);
  }

  function clearBadge(type) {
    if (type === 'messages') setUnreadMessages(0);
    if (type === 'appointments') setPendingAppointments(0);
    if (type === 'alerts') setActiveAlerts(0);
  }

  return (
    <SocketContext.Provider value={{
      socket: socketRef.current,
      unreadMessages,
      pendingAppointments,
      activeAlerts,
      addListener,
      removeListener,
      clearBadge
    }}>
      {children}
    </SocketContext.Provider>
  );
}

export const useSocket = () => useContext(SocketContext);
```

### 4. Frontend — App.jsx
Wrap the entire app:

```jsx
import { SocketProvider } from './context/SocketContext';

function App() {
  const [user, setUser] = useState(null); // from JWT decode on login

  return (
    <SocketProvider user={user}>
      <Navbar />
      <Routes>...</Routes>
    </SocketProvider>
  );
}
```

### 5. Frontend — Navbar.jsx
Read badge counts from SocketContext:

```jsx
import { useSocket } from '../context/SocketContext';

function Navbar() {
  const { unreadMessages, pendingAppointments, activeAlerts } = useSocket();

  return (
    <nav>
      <NavItem icon="message" badge={unreadMessages} label="Messages" />
      <NavItem icon="calendar" badge={pendingAppointments} label="Appointments" />
      <NavItem icon="bell" badge={activeAlerts} label="Alerts" color="red" />
    </nav>
  );
}
```

### 6. Frontend — How page components use addListener
Every page component that needs real-time updates should do this pattern:

```jsx
import { useSocket } from '../context/SocketContext';
import { useEffect, useState } from 'react';

function DoctorAppointments() {
  const { addListener, removeListener, clearBadge } = useSocket();
  const [pendingList, setPendingList] = useState([]);

  useEffect(() => {
    // Register listener when component mounts
    const handleNewAppointment = (data) => {
      setPendingList(prev => [data, ...prev]);
    };
    addListener('new_appointment', handleNewAppointment);
    clearBadge('appointments');

    // Remove listener when component unmounts
    return () => removeListener('new_appointment', handleNewAppointment);
  }, []);
}
```

## Acceptance Criteria
- [ ] Single socket connection created on login, destroyed on logout
- [ ] Unread message badge in Navbar updates when message arrives on ANY page
- [ ] Pending appointment badge in Navbar updates when booking arrives on ANY page
- [ ] Alert badge in Navbar updates when alert fires on ANY page
- [ ] Medication reminder shows browser notification regardless of current page
- [ ] Page components can subscribe to events when mounted and unsubscribe on unmount
- [ ] Socket reconnects automatically if connection drops
