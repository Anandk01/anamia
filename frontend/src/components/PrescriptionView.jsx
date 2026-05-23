import React, { useState, useEffect } from 'react';
import { FileText, ChevronDown, ChevronUp, Download, Pill, User } from 'lucide-react';
import client from '../api/client';

export default function PrescriptionView() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [doctors, setDoctors] = useState([]);

  useEffect(() => {
    client.get('/api/prescriptions/mine')
      .then(res => setPrescriptions(res.data?.prescriptions || []))
      .catch(() => {});

    // Fetch list of doctors
    client.get('/api/appointments/doctors')
      .then(res => setDoctors(res.data?.doctors || []))
      .catch(() => {});
  }, []);

  function toggle(id) {
    setExpanded(expanded === id ? null : id);
  }

  async function downloadPdf(id) {
    try {
      const res = await client.get(`/api/prescriptions/${id}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `prescription_${id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {}
  }

  function printPrescription(rx) {
    const content = `
      <html><head><title>Prescription - AnemiaCare</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 40px; color: #1e293b; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #6366f1; padding-bottom: 15px; }
        .header h1 { color: #6366f1; margin: 0 0 5px 0; font-size: 24px; }
        .header p { color: #64748b; margin: 0; font-size: 12px; }
        .doctor-info { background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 20px; }
        .doctor-info h2 { margin: 0 0 5px 0; font-size: 16px; color: #334155; }
        .doctor-info p { margin: 2px 0; font-size: 13px; color: #64748b; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; font-size: 13px; }
        th { background: #f1f5f9; font-weight: 600; color: #475569; }
        .section { margin: 15px 0; padding: 12px; border-radius: 8px; }
        .section-title { font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }
        .diet-section { background: #f0fdf4; border: 1px solid #bbf7d0; }
        .diet-section .section-title { color: #166534; }
        .instructions-section { background: #eff6ff; border: 1px solid #bfdbfe; }
        .instructions-section .section-title { color: #1e40af; }
        .notes-section { background: #fefce8; border: 1px solid #fde68a; }
        .notes-section .section-title { color: #92400e; }
        .followup { margin-top: 15px; padding: 10px; background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px; font-size: 13px; color: #6b21a8; }
        .footer { margin-top: 30px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 10px; text-align: center; }
      </style>
      </head><body>
      <div class="header">
        <h1>AnemiaCare</h1>
        <p>Digital Health Platform for Anemia Management</p>
      </div>
      <div class="doctor-info">
        <h2>Dr. ${rx.doctor_name || rx.doctor_username || rx.doctor_id}</h2>
        <p><strong>Date Prescribed:</strong> ${new Date(rx.created_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
      <h3 style="font-size:14px; color:#334155; margin-bottom:5px;">Medications</h3>
      <table><thead><tr><th>Medicine</th><th>Dose</th><th>Frequency</th><th>Duration</th></tr></thead><tbody>
      ${(rx.medications || []).map(m => `<tr><td>${m.name}</td><td>${m.dose}</td><td>${m.frequency}</td><td>${m.duration}</td></tr>`).join('')}
      </tbody></table>
      ${rx.dosage_instructions ? `<div class="section instructions-section"><p class="section-title">Dosage Instructions</p><p style="margin:0;font-size:13px;">${rx.dosage_instructions}</p></div>` : ''}
      ${rx.diet_plan ? `<div class="section diet-section"><p class="section-title">Diet Plan</p><p style="margin:0;font-size:13px;white-space:pre-wrap;">${rx.diet_plan}</p></div>` : ''}
      ${rx.notes ? `<div class="section notes-section"><p class="section-title">Notes</p><p style="margin:0;font-size:13px;">${rx.notes}</p></div>` : ''}
      ${rx.follow_up_date ? `<div class="followup">📅 <strong>Follow-up Date:</strong> ${rx.follow_up_date}</div>` : ''}
      <div class="footer">
        <p>This is a computer-generated prescription from AnemiaCare.</p>
        <p>Not a substitute for professional medical advice. Please consult your doctor for any concerns.</p>
      </div>
      </body></html>
    `;
    const win = window.open('', '_blank');
    win.document.write(content);
    win.document.close();
    win.print();
  }

  return (
    <div className="space-y-4">
      {/* App Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
          <span className="text-white font-bold text-sm">A</span>
        </div>
        <div>
          <h1 className="text-lg font-bold text-indigo-700">AnemiaCare</h1>
          <p className="text-xs text-slate-400">My Prescriptions</p>
        </div>
      </div>

      {/* Doctor List */}
      {doctors.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-3">
          <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Your Doctors</p>
          <div className="flex flex-wrap gap-2">
            {doctors.map(doc => (
              <div key={doc.id} className="flex items-center gap-1.5 bg-indigo-50 border border-indigo-100 rounded-full px-3 py-1">
                <User size={12} className="text-indigo-500" />
                <span className="text-xs font-medium text-indigo-700">{doc.name || doc.username}</span>
                {doc.specialization && <span className="text-xs text-indigo-400">· {doc.specialization}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prescriptions List */}
      {prescriptions.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          <FileText size={32} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">No prescriptions yet</p>
        </div>
      )}

      {prescriptions.map(rx => (
        <div key={rx.id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div
            className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-slate-50 transition"
            onClick={() => toggle(rx.id)}
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Pill size={14} className="text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">Dr. {rx.doctor_name || rx.doctor_username}</p>
                <p className="text-xs text-slate-400">{new Date(rx.created_at).toLocaleDateString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs bg-indigo-100 text-indigo-700 font-medium px-2 py-0.5 rounded-full">
                {rx.medications?.length || 0} meds
              </span>
              {rx.follow_up_date && (
                <span className="text-xs bg-purple-100 text-purple-700 font-medium px-2 py-0.5 rounded-full">
                  Follow-up
                </span>
              )}
              {expanded === rx.id ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
            </div>
          </div>

          {expanded === rx.id && (
            <div className="border-t border-slate-100 px-4 py-3 space-y-3">
              {/* Doctor & Date */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div>
                  <p className="text-sm font-semibold text-slate-700">Dr. {rx.doctor_name || rx.doctor_username}</p>
                  <p className="text-xs text-slate-500">Prescribed on {new Date(rx.created_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                </div>
              </div>

              {/* Medications Table */}
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Medications & Timing</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 uppercase bg-slate-50">
                      <th className="text-left py-2 px-2 rounded-l-lg">Medicine</th>
                      <th className="text-left py-2 px-2">Dose</th>
                      <th className="text-left py-2 px-2">Frequency</th>
                      <th className="text-left py-2 px-2 rounded-r-lg">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {(rx.medications || []).map((med, idx) => (
                      <tr key={idx}>
                        <td className="py-2 px-2 text-slate-700 font-medium">{med.name}</td>
                        <td className="py-2 px-2 text-slate-600">{med.dose}</td>
                        <td className="py-2 px-2 text-slate-600">{med.frequency}</td>
                        <td className="py-2 px-2 text-slate-600">{med.duration}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Dosage Instructions */}
              {rx.dosage_instructions && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-blue-700 uppercase mb-1">Dosage Instructions</p>
                  <p className="text-sm text-blue-800 whitespace-pre-wrap">{rx.dosage_instructions}</p>
                </div>
              )}

              {/* Diet Plan */}
              {rx.diet_plan && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-green-700 uppercase mb-1">Diet Plan</p>
                  <p className="text-sm text-green-800 whitespace-pre-wrap">{rx.diet_plan}</p>
                </div>
              )}

              {/* Notes */}
              {rx.notes && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Notes</p>
                  <p className="text-sm text-amber-800 whitespace-pre-wrap">{rx.notes}</p>
                </div>
              )}

              {/* Follow-up Date */}
              {rx.follow_up_date && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 flex items-center gap-2">
                  <span className="text-lg">📅</span>
                  <div>
                    <p className="text-xs font-semibold text-purple-700 uppercase">Follow-up Date</p>
                    <p className="text-sm font-medium text-purple-800">{rx.follow_up_date}</p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1">
                <button
                  onClick={() => downloadPdf(rx.id)}
                  className="flex items-center gap-1.5 text-xs text-indigo-600 font-medium hover:text-indigo-800"
                >
                  <Download size={12} /> Download PDF
                </button>
                <button
                  onClick={() => printPrescription(rx)}
                  className="flex items-center gap-1.5 text-xs text-slate-600 font-medium hover:text-slate-800"
                >
                  🖨️ Print
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
