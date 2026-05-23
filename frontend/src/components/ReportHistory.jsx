/**
 * ReportHistory.jsx
 * Dense paginated table with slide-in drawer for full detail.
 */

import { useState, useEffect } from 'react';
import { Download, X } from 'lucide-react';
import client from '../api/client.js';
import { downloadPDF } from '../services/pdfService.js';

const SEVERITY_BADGE = {
  None:     'bg-emerald-100 text-emerald-700',
  Mild:     'bg-amber-100 text-amber-700',
  Moderate: 'bg-orange-100 text-orange-700',
  Severe:   'bg-red-100 text-red-700',
};

export default function ReportHistory({ username, role }) {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [drawer, setDrawer] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(null);
  const [searchUsername, setSearchUsername] = useState('');

  async function fetchPage(p) {
    setLoading(true);
    setError(null);
    try {
      const url = searchUsername
        ? `/api/reports?page=${p}&username=${searchUsername}`
        : `/api/reports?page=${p}`;
      const res = await client.get(url);
      setRecords(res.data.records || []);
      setTotal(res.data.total || 0);
      setPages(res.data.pages || 1);
      setPage(p);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load reports.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchPage(1); }, [username]);

  async function handleDownload(e, record) {
    e.stopPropagation();
    setPdfLoading(record.prediction_id);
    try {
      await downloadPDF(record, record.username || username);
    } catch {
      // silently fail — PDFDownloadButton handles toasts
    } finally {
      setPdfLoading(null);
    }
  }

  return (
    <div className="relative">
      {/* Table */}
      <div className="bg-white rounded border border-slate-200 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Report History {total > 0 && `(${total})`}
          </span>
          <button onClick={() => fetchPage(page)} className="text-xs text-indigo-600 hover:text-indigo-800 transition">
            ↻ Refresh
          </button>
        </div>

        {role === 'doctor' && (
          <div className="px-4 py-2 border-b border-slate-100">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchUsername}
                onChange={e => setSearchUsername(e.target.value)}
                placeholder="Search by patient username..."
                className="flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button onClick={() => fetchPage(1)} className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700">Search</button>
              {searchUsername && <button onClick={() => { setSearchUsername(''); fetchPage(1); }} className="px-3 py-1.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-200">Clear</button>}
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-10 text-slate-400 text-sm gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Loading...
          </div>
        )}

        {error && !loading && (
          <div className="px-4 py-3 text-sm text-red-600 bg-red-50">{error}</div>
        )}

        {!loading && !error && records.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-sm gap-2">
            <span className="text-2xl">📋</span>
            <p>No records found</p>
          </div>
        )}

        {!loading && records.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                <tr>
                  {role === 'doctor' && <th className="px-3 py-2 text-left">Username</th>}
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">HGB</th>
                  <th className="px-3 py-2 text-left">Severity</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Result</th>
                  <th className="px-3 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {records.map((rec) => (
                  <tr
                    key={rec.prediction_id}
                    className="hover:bg-slate-50 transition cursor-pointer"
                    style={{ height: '36px' }}
                    onClick={() => setDrawer(rec)}
                  >
                    {role === 'doctor' && <td className="px-3 py-1.5 text-slate-600 text-xs font-medium">{rec.username || '—'}</td>}
                    <td className="px-3 py-1.5 text-slate-500 text-xs whitespace-nowrap">{rec.date?.slice(0, 10)}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-700">{rec.hgb}</td>
                    <td className="px-3 py-1.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SEVERITY_BADGE[rec.severity_level] || 'bg-slate-100 text-slate-600'}`}>
                        {rec.severity_level}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-slate-600 text-xs">{rec.anemia_type}</td>
                    <td className="px-3 py-1.5 text-xs">
                      {rec.anemia_detected ? (
                        <span className="text-red-600 font-medium">Anemia</span>
                      ) : (
                        <span className="text-emerald-600 font-medium">Normal</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5">
                      <button
                        onClick={(e) => handleDownload(e, rec)}
                        disabled={pdfLoading === rec.prediction_id}
                        className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition disabled:opacity-50"
                      >
                        <Download size={12} />
                        {pdfLoading === rec.prediction_id ? '...' : 'PDF'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-slate-100">
            <span className="text-xs text-slate-400">Page {page} of {pages}</span>
            <div className="flex gap-1">
              <button
                onClick={() => fetchPage(page - 1)}
                disabled={page <= 1}
                className="px-2.5 py-1 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 transition"
              >
                ←
              </button>
              <button
                onClick={() => fetchPage(page + 1)}
                disabled={page >= pages}
                className="px-2.5 py-1 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 transition"
              >
                →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Slide-in drawer */}
      {drawer && (
        <>
          <div
            className="fixed inset-0 bg-black/20 z-40"
            onClick={() => setDrawer(null)}
          />
          <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-800">Report Detail</h3>
              <button onClick={() => setDrawer(null)} className="text-slate-400 hover:text-slate-600 transition">
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4 text-sm">
              <div className="space-y-2">
                <p><span className="font-semibold text-slate-500">Date:</span> <span className="text-slate-700">{drawer.date}</span></p>
                <p><span className="font-semibold text-slate-500">HGB:</span> <span className="text-slate-700">{drawer.hgb} g/dL</span></p>
                <p><span className="font-semibold text-slate-500">Severity:</span> <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SEVERITY_BADGE[drawer.severity_level] || ''}`}>{drawer.severity_level}</span></p>
                <p><span className="font-semibold text-slate-500">Type:</span> <span className="text-slate-700">{drawer.anemia_type}</span></p>
                <p><span className="font-semibold text-slate-500">Confidence:</span> <span className="text-slate-700">{drawer.confidence ? `${(drawer.confidence * 100).toFixed(1)}%` : 'N/A'}</span></p>
              </div>
              <div>
                <p className="font-semibold text-slate-500 mb-1">CBC Values</p>
                <div className="grid grid-cols-2 gap-1 text-xs">
                  {['rbc','mcv','mch','mchc','rdw','tlc','plt','hgb'].map((k) => (
                    <div key={k} className="flex justify-between bg-slate-50 rounded px-2 py-1">
                      <span className="font-medium text-slate-500 uppercase">{k}</span>
                      <span className="text-slate-700">{drawer[k]}</span>
                    </div>
                  ))}
                </div>
              </div>
              {Array.isArray(drawer.explanation) && drawer.explanation.length > 0 && (
                <div>
                  <p className="font-semibold text-slate-500 mb-1">SHAP Explanation</p>
                  {drawer.explanation.slice(0, 3).map((e, i) => (
                    <div key={i} className="flex justify-between text-xs bg-slate-50 rounded px-2 py-1 mb-1">
                      <span className="font-medium text-slate-600">{e.feature}</span>
                      <span className="text-slate-500">{e.direction}</span>
                      <span className="text-slate-700">{e.shap_value?.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="px-5 py-4 border-t border-slate-100">
              <button
                onClick={(e) => handleDownload(e, drawer)}
                className="w-full flex items-center justify-center gap-2 text-white font-semibold py-2 rounded text-sm transition"
                style={{ backgroundColor: '#6366f1' }}
              >
                <Download size={14} />
                Download PDF
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
