/**
 * PDFDownloadButton.jsx
 * Download icon button with loading spinner, success/error toasts.
 */

import { useState, useEffect } from 'react';
import { Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { downloadPDF, generateFilename } from '../services/pdfService.js';

function Toast({ type, message, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [onClose]);

  const styles = type === 'success'
    ? 'bg-emerald-600 text-white'
    : 'bg-red-600 text-white';

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2.5 rounded shadow-lg text-sm font-medium ${styles}`}
    >
      {type === 'success' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
      {message}
      <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100">×</button>
    </div>
  );
}

export default function PDFDownloadButton({ reportData, username }) {
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  async function handleDownload() {
    if (loading || !reportData) return;
    setLoading(true);
    setToast(null);
    try {
      await downloadPDF(reportData, username);
      const dateStr = reportData.date || new Date().toISOString().replace('T', ' ').slice(0, 19);
      const filename = generateFilename(username, dateStr);
      setToast({ type: 'success', message: `Downloaded: ${filename}` });
    } catch (err) {
      console.error('PDF error:', err);
      setToast({ type: 'error', message: 'Failed to generate PDF. Retry?' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={handleDownload}
        disabled={loading || !reportData}
        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600 transition disabled:opacity-50"
        title="Download PDF Report"
      >
        {loading ? (
          <Loader2 size={13} className="animate-spin" />
        ) : (
          <Download size={13} />
        )}
        {loading ? 'Generating...' : 'Download Report'}
      </button>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}
    </>
  );
}
