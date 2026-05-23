import React, { useState, useEffect } from 'react';
import { FileText, ChevronDown, ChevronUp, Download, Pill } from 'lucide-react';
import client from '../api/client';

export default function PrescriptionView() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    client.get('/api/prescriptions/mine')
      .then(res => setPrescriptions(res.data?.prescriptions || []))
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
    const meds = (rx.medications || []).map(m => `${m.name} - ${m.dose} - ${m.frequency} - ${m.duration}`).join('\n');
    const content = `
      <html><head><title>Prescription</title>
      <style>body{font-family:Arial,sans-serif;padding:40px;} h1{color:#4f46e5;} table{width:100%;border-collapse:collapse;margin:20px 0;} th,td{border:1px solid #ddd;padding:8px;text-align:left;} th{background:#f1f5f9;} .footer{margin-top:30px;font-size:12px;color:#666;border-top:1px solid #ddd;padding-top:10px;}</style>
      </head><body>
      <h1>AnemiaCare Prescription</h1>
      <p><strong>Doctor:</strong> Dr. ${rx.doctor_name || rx.doctor_username || rx.doctor_id}</p>
      <p><strong>Date:</strong> ${new Date(rx.created_at).toLocaleDateString()}</p>
      <hr/>
      <h3>Medications</h3>
      <table><thead><tr><th>Medicine</th><th>Dose</th><th>Frequency</th><th>Duration</th></tr></thead><tbody>
      ${(rx.medications || []).map(m => `<tr><td>${m.name}</td><td>${m.dose}</td><td>${m.frequency}</td><td>${m.duration}</td></tr>`).join('')}
      </tbody></table>
      ${rx.dosage_instructions ? `<p><strong>Instructions:</strong> ${rx.dosage_instructions}</p>` : ''}
      ${rx.diet_plan ? `<p><strong>Diet Plan:</strong> ${rx.diet_plan}</p>` : ''}
      ${rx.notes ? `<p><strong>Notes:</strong> ${rx.notes}</p>` : ''}
      ${rx.follow_up_date ? `<p><strong>Follow-up Date:</strong> ${rx.follow_up_date}</p>` : ''}
      <div class="footer"><p>This is a computer-generated prescription from AnemiaCare.</p><p>Not a substitute for professional medical advice.</p></div>
      </body></html>
    `;
    const win = window.open('', '_blank');
    win.document.write(content);
    win.document.close();
    win.print();
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">My Prescriptions</h2>

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
              {expanded === rx.id ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
            </div>
          </div>

          {expanded === rx.id && (
            <div className="border-t border-slate-100 px-4 py-3 space-y-3">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 uppercase">
                    <th className="text-left py-1">Medication</th>
                    <th className="text-left py-1">Dose</th>
                    <th className="text-left py-1">Frequency</th>
                    <th className="text-left py-1">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {(rx.medications || []).map((med, idx) => (
                    <tr key={idx}>
                      <td className="py-1.5 text-slate-700 font-medium">{med.name}</td>
                      <td className="py-1.5 text-slate-600">{med.dose}</td>
                      <td className="py-1.5 text-slate-600">{med.frequency}</td>
                      <td className="py-1.5 text-slate-600">{med.duration}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rx.diet_plan && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-green-700 uppercase mb-1">Diet Plan</p>
                  <p className="text-sm text-green-800 whitespace-pre-wrap">{rx.diet_plan}</p>
                </div>
              )}
              {rx.notes && <p className="text-xs text-slate-500 italic">{rx.notes}</p>}
              {rx.dosage_instructions && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-blue-700 uppercase mb-1">Dosage Instructions</p>
                  <p className="text-sm text-blue-800 whitespace-pre-wrap">{rx.dosage_instructions}</p>
                </div>
              )}
              {rx.follow_up_date && (
                <p className="text-xs text-slate-600">📅 Follow-up: <span className="font-medium">{rx.follow_up_date}</span></p>
              )}
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
