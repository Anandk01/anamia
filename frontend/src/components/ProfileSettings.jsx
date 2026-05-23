import React, { useState, useEffect } from 'react';
import { User, Bell, Eye, Shield, Save } from 'lucide-react';
import client from '../api/client';

const TABS = [
  { id: 'personal', label: 'Personal Info', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'accessibility', label: 'Accessibility', icon: Eye },
  { id: 'security', label: 'Security', icon: Shield },
];

const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const CONDITIONS = ['Diabetes', 'Hypertension', 'Thyroid', 'Kidney Disease', 'Heart Disease', 'Asthma'];
const DIETARY_PREFS = ['Vegetarian', 'Vegan', 'Non-Vegetarian', 'Pescatarian', 'Gluten-Free'];
const NOTIF_ROWS = ['medication', 'appointment', 'alert', 'forum'];

export default function ProfileSettings() {
  const [tab, setTab] = useState('personal');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Personal info
  const [fullName, setFullName] = useState('');
  const [bloodType, setBloodType] = useState('');
  const [conditions, setConditions] = useState([]);
  const [dietary, setDietary] = useState([]);
  const [emergencyName, setEmergencyName] = useState('');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [emergencyRelation, setEmergencyRelation] = useState('');
  const [age, setAge] = useState('');
  const [sex, setSex] = useState('');

  // Notifications
  const [notifPrefs, setNotifPrefs] = useState({});

  // Accessibility
  const [fontSize, setFontSize] = useState('M');
  const [highContrast, setHighContrast] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  // Security
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');

  useEffect(() => {
    client.get('/api/profile')
      .then(res => {
        const d = res.data?.profile || res.data || {};
        setFullName(d.full_name || '');
        setBloodType(d.blood_type || '');
        setConditions(d.known_conditions || d.conditions || []);
        setDietary(d.dietary_preferences || []);
        setEmergencyName(d.emergency_contact?.name || '');
        setEmergencyPhone(d.emergency_contact?.phone || '');
        setEmergencyRelation(d.emergency_contact?.relation || '');
        setAge(d.age || '');
        setSex(d.sex !== null && d.sex !== undefined ? String(d.sex) : '');
        setNotifPrefs(d.notification_prefs || d.notification_preferences || {});
        setFontSize(d.font_size || 'M');
        setHighContrast(d.high_contrast || false);
        setReducedMotion(d.reduced_motion || false);
      })
      .catch(() => {});

    // Apply saved accessibility settings on mount
    const savedFont = localStorage.getItem('anemia-font-size');
    if (savedFont) {
      setFontSize(savedFont);
      const html = document.documentElement;
      html.classList.remove('text-sm', 'text-base', 'text-lg');
      html.classList.add(savedFont === 'S' ? 'text-sm' : savedFont === 'L' ? 'text-lg' : 'text-base');
    }
    if (localStorage.getItem('anemia-high-contrast') === '1') {
      setHighContrast(true);
      document.documentElement.classList.add('high-contrast');
    }
  }, []);

  function toggleCondition(c) {
    setConditions(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);
  }

  function toggleDietary(d) {
    setDietary(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
  }

  function toggleNotif(row, col) {
    setNotifPrefs(prev => {
      const key = `${row}_${col}`;
      return { ...prev, [key]: !prev[key] };
    });
  }

  async function savePersonal() {
    setSaving(true);
    try {
      await client.put('/api/profile', {
        full_name: fullName,
        age: age ? parseInt(age) : null,
        sex: sex !== '' ? parseInt(sex) : null,
        blood_type: bloodType,
        known_conditions: conditions,
        dietary_preferences: dietary,
        emergency_contact: { name: emergencyName, phone: emergencyPhone, relation: emergencyRelation },
      });
      setMessage('Personal info saved');
    } catch { setMessage('Failed to save'); }
    setSaving(false);
    setTimeout(() => setMessage(null), 3000);
  }

  async function saveNotifications() {
    setSaving(true);
    try {
      await client.put('/api/profile/preferences', { notification_preferences: notifPrefs });
      setMessage('Notification preferences saved');
    } catch { setMessage('Failed to save'); }
    setSaving(false);
    setTimeout(() => setMessage(null), 3000);
  }

  async function saveAccessibility() {
    setSaving(true);
    try {
      await client.put('/api/profile/preferences', {
        accessibility: { font_size: fontSize, high_contrast: highContrast, reduced_motion: reducedMotion },
      });
      setMessage('Accessibility settings saved');
    } catch { setMessage('Failed to save'); }
    setSaving(false);
    setTimeout(() => setMessage(null), 3000);
  }

  async function changePassword(e) {
    e.preventDefault();
    if (newPw !== confirmPw) { setMessage('Passwords do not match'); return; }
    setSaving(true);
    try {
      await client.put('/api/profile', { current_password: currentPw, new_password: newPw });
      setMessage('Password changed');
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    } catch (err) { setMessage(err.response?.data?.message || 'Failed to change password'); }
    setSaving(false);
    setTimeout(() => setMessage(null), 3000);
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Settings</h2>

      {message && (
        <div className={`text-sm px-3 py-2 rounded-lg ${message.includes('Failed') || message.includes('match') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
          {message}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
              tab === t.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            <t.icon size={13} /> {t.label}
          </button>
        ))}
      </div>

      {/* Personal Info */}
      {tab === 'personal' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Full Name</label>
            <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Enter your full name" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Age</label>
              <input type="number" value={age} onChange={e => setAge(e.target.value)} min="1" max="120" placeholder="Enter age" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Sex</label>
              <div className="flex gap-3 mt-1">
                <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="radio" name="sex" value="0" checked={sex === '0'} onChange={e => setSex(e.target.value)} className="text-indigo-500 focus:ring-indigo-500" /> Male
                </label>
                <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="radio" name="sex" value="1" checked={sex === '1'} onChange={e => setSex(e.target.value)} className="text-indigo-500 focus:ring-indigo-500" /> Female
                </label>
              </div>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Blood Type</label>
            <select value={bloodType} onChange={e => setBloodType(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="">Select...</option>
              {BLOOD_TYPES.map(bt => <option key={bt} value={bt}>{bt}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Conditions</label>
            <div className="flex flex-wrap gap-2">
              {CONDITIONS.map(c => (
                <button key={c} type="button" onClick={() => toggleCondition(c)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${conditions.includes(c) ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600'}`}>{c}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Dietary Preferences</label>
            <div className="flex flex-wrap gap-2">
              {DIETARY_PREFS.map(d => (
                <button key={d} type="button" onClick={() => toggleDietary(d)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${dietary.includes(d) ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600'}`}>{d}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Emergency Contact</label>
            <div className="grid grid-cols-3 gap-2">
              <input type="text" placeholder="Name" value={emergencyName} onChange={e => setEmergencyName(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <input type="tel" placeholder="Phone" value={emergencyPhone} onChange={e => setEmergencyPhone(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <input type="text" placeholder="Relation" value={emergencyRelation} onChange={e => setEmergencyRelation(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>
          <button onClick={savePersonal} disabled={saving} className="flex items-center gap-2 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60">
            <Save size={14} /> Save
          </button>
        </div>
      )}

      {/* Notifications */}
      {tab === 'notifications' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase">
                <th className="text-left py-2">Type</th>
                <th className="text-center py-2">Email</th>
                <th className="text-center py-2">Push</th>
              </tr>
            </thead>
            <tbody>
              {NOTIF_ROWS.map(row => (
                <tr key={row} className="border-t border-slate-100">
                  <td className="py-3 capitalize font-medium text-slate-700">{row}</td>
                  <td className="py-3 text-center">
                    <input type="checkbox" checked={!!notifPrefs[`${row}_email`]} onChange={() => toggleNotif(row, 'email')} className="rounded text-indigo-500 focus:ring-indigo-500" />
                  </td>
                  <td className="py-3 text-center">
                    <input type="checkbox" checked={!!notifPrefs[`${row}_push`]} onChange={() => toggleNotif(row, 'push')} className="rounded text-indigo-500 focus:ring-indigo-500" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={saveNotifications} disabled={saving} className="flex items-center gap-2 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60">
            <Save size={14} /> Save
          </button>
        </div>
      )}

      {/* Accessibility */}
      {tab === 'accessibility' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Font Size</label>
            <div className="flex gap-2">
              {['S', 'M', 'L'].map(s => (
                <button key={s} onClick={() => {
                  setFontSize(s);
                  const html = document.documentElement;
                  html.classList.remove('text-sm', 'text-base', 'text-lg');
                  html.classList.add(s === 'S' ? 'text-sm' : s === 'M' ? 'text-base' : 'text-lg');
                  localStorage.setItem('anemia-font-size', s);
                }} className={`px-4 py-2 rounded-lg text-sm font-medium transition ${fontSize === s ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {s === 'S' ? 'Small' : s === 'M' ? 'Medium' : 'Large'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-slate-700">High Contrast</span>
            <button onClick={() => {
              const next = !highContrast;
              setHighContrast(next);
              const html = document.documentElement;
              if (next) { html.classList.add('high-contrast'); } else { html.classList.remove('high-contrast'); }
              localStorage.setItem('anemia-high-contrast', next ? '1' : '0');
            }} className={`w-10 h-5 rounded-full transition ${highContrast ? 'bg-indigo-500' : 'bg-slate-300'}`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${highContrast ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-slate-700">Reduced Motion</span>
            <button onClick={() => setReducedMotion(!reducedMotion)} className={`w-10 h-5 rounded-full transition ${reducedMotion ? 'bg-indigo-500' : 'bg-slate-300'}`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${reducedMotion ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
          <button onClick={saveAccessibility} disabled={saving} className="flex items-center gap-2 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60">
            <Save size={14} /> Save
          </button>
        </div>
      )}

      {/* Security */}
      {tab === 'security' && (
        <form onSubmit={changePassword} className="bg-white rounded-lg border border-slate-200 p-5 space-y-4 max-w-md">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Current Password</label>
            <input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">New Password</label>
            <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Confirm Password</label>
            <input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <button type="submit" disabled={saving} className="flex items-center gap-2 bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-60">
            <Shield size={14} /> Change Password
          </button>
        </form>
      )}
    </div>
  );
}
