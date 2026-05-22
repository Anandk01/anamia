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
              {rx.notes && <p className="text-xs text-slate-500 italic">{rx.notes}</p>}
              <button
                onClick={() => downloadPdf(rx.id)}
                className="flex items-center gap-1.5 text-xs text-indigo-600 font-medium hover:text-indigo-800"
              >
                <Download size={12} /> Download PDF
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
