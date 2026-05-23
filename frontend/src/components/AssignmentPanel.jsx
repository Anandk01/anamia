/**
 * AssignmentPanel.jsx
 * Admin component for managing doctor-patient assignments.
 * Shows doctors list with patient counts, assigned patients, and add/remove functionality.
 */

import { useState, useEffect } from 'react';
import { Users, X, Plus, Search, UserPlus, Loader2 } from 'lucide-react';
import client from '../api/client.js';

function AddPatientModal({ doctor, onClose, onAssigned }) {
  const [unassigned, setUnassigned] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    client.get('/api/unassigned-patients')
      .then(res => setUnassigned(res.data?.patients || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = unassigned.filter(p =>
    p.username.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  function toggleSelect(username) {
    setSelected(prev => prev.includes(username)
      ? prev.filter(u => u !== username)
      : [...prev, username]
    );
  }

  async function handleAssign() {
    if (selected.length === 0) return;
    setAssigning(true);
    try {
      await client.post('/api/assign', {
        doctor_username: doctor,
        patient_usernames: selected,
      });
      onAssigned();
      onClose();
    } catch {
      // silent
    } finally {
      setAssigning(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              Assign Patients to <span className="text-indigo-600">{doctor}</span>
            </h3>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
          </div>

          <div className="px-5 py-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search unassigned patients..."
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 pb-3">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 size={20} className="animate-spin text-indigo-500" />
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">No unassigned patients found</p>
            ) : (
              <div className="space-y-1">
                {filtered.map(p => (
                  <label key={p.username} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selected.includes(p.username)}
                      onChange={() => toggleSelect(p.username)}
                      className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{p.username}</p>
                      <p className="text-xs text-slate-400 truncate">{p.email}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="px-5 py-4 border-t border-slate-200 dark:border-slate-700">
            <button
              onClick={handleAssign}
              disabled={selected.length === 0 || assigning}
              className="w-full bg-indigo-500 text-white font-semibold py-2 rounded-lg text-sm hover:bg-indigo-600 disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              {assigning ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
              Assign {selected.length > 0 ? `(${selected.length})` : ''}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default function AssignmentPanel() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [showModal, setShowModal] = useState(false);

  function fetchAssignments() {
    setLoading(true);
    client.get('/api/assignments')
      .then(res => setAssignments(res.data?.assignments || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { fetchAssignments(); }, []);

  // Group assignments by doctor
  const doctorMap = {};
  assignments.forEach(a => {
    if (!doctorMap[a.doctor_username]) doctorMap[a.doctor_username] = [];
    doctorMap[a.doctor_username].push(a);
  });
  const doctors = Object.keys(doctorMap);

  async function handleUnassign(doctorUsername, patientUsername) {
    try {
      await client.delete('/api/unassign', {
        data: { doctor_username: doctorUsername, patient_username: patientUsername }
      });
      fetchAssignments();
    } catch {
      // silent
    }
  }

  const selectedPatients = selectedDoctor ? (doctorMap[selectedDoctor] || []) : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Doctor–Patient Assignments</h2>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-indigo-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left: Doctors list */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Doctors</p>
            </div>
            <div className="divide-y divide-slate-50 dark:divide-slate-700">
              {doctors.length === 0 ? (
                <p className="text-sm text-slate-400 px-4 py-6 text-center">No assignments yet</p>
              ) : (
                doctors.map(doc => (
                  <button
                    key={doc}
                    onClick={() => setSelectedDoctor(doc)}
                    className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition ${
                      selectedDoctor === doc ? 'bg-indigo-50 dark:bg-indigo-900/20 border-l-3 border-indigo-500' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                        <Users size={14} className="text-indigo-600" />
                      </div>
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{doc}</span>
                    </div>
                    <span className="text-xs font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300 px-2 py-0.5 rounded-full">
                      {doctorMap[doc].length}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right: Selected doctor's patients */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                {selectedDoctor ? `Patients of ${selectedDoctor}` : 'Select a doctor'}
              </p>
              {selectedDoctor && (
                <button
                  onClick={() => setShowModal(true)}
                  className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition"
                >
                  <Plus size={12} /> Add Patient
                </button>
              )}
            </div>
            <div className="divide-y divide-slate-50 dark:divide-slate-700">
              {!selectedDoctor ? (
                <p className="text-sm text-slate-400 px-4 py-6 text-center">Click a doctor to view patients</p>
              ) : selectedPatients.length === 0 ? (
                <p className="text-sm text-slate-400 px-4 py-6 text-center">No patients assigned</p>
              ) : (
                selectedPatients.map(a => (
                  <div key={a.patient_username} className="flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{a.patient_username}</p>
                      <p className="text-xs text-slate-400">{a.assigned_at ? `Assigned ${a.assigned_at}` : ''}</p>
                    </div>
                    <button
                      onClick={() => handleUnassign(selectedDoctor, a.patient_username)}
                      className="text-red-400 hover:text-red-600 transition"
                      title="Remove assignment"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {showModal && selectedDoctor && (
        <AddPatientModal
          doctor={selectedDoctor}
          onClose={() => setShowModal(false)}
          onAssigned={fetchAssignments}
        />
      )}
    </div>
  );
}
