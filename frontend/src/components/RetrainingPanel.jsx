/**
 * RetrainingPanel.jsx
 * CSV dropzone, metrics bars, Approve/Rollback buttons.
 */

import { useState, useRef } from 'react';
import { Upload, CheckCircle, RotateCcw } from 'lucide-react';
import client from '../api/client.js';

function MetricBar({ label, value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-500 font-medium">{label}</span>
        <span className="text-slate-700 font-semibold">{pct}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: '#6366f1' }}
        />
      </div>
    </div>
  );
}

export default function RetrainingPanel() {
  const [status, setStatus] = useState(null); // null | 'uploading' | 'training' | 'pending_approval' | 'approved' | 'rolled_back' | 'error'
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  async function handleFile(file) {
    if (!file || !file.name.endsWith('.csv')) {
      setError('Please upload a CSV file.');
      return;
    }
    setError(null);
    setStatus('uploading');
    try {
      const fd = new FormData();
      fd.append('file', file);
      const uploadRes = await client.post('/api/retrain/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setStatus('training');
      const startRes = await client.post('/api/retrain/start', {
        filename: uploadRes.data?.filename,
      });
      setMetrics(startRes.data?.metrics || null);
      setStatus('pending_approval');
    } catch (err) {
      setError(err.response?.data?.message || 'Retraining failed.');
      setStatus('error');
    }
  }

  async function handleApprove() {
    try {
      await client.post('/api/retrain/approve');
      setStatus('approved');
    } catch (err) {
      setError(err.response?.data?.message || 'Approval failed.');
    }
  }

  async function handleRollback() {
    try {
      await client.post('/api/retrain/rollback');
      setStatus('rolled_back');
      setMetrics(null);
    } catch (err) {
      setError(err.response?.data?.message || 'Rollback failed.');
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        className={`rounded border-2 border-dashed p-8 text-center cursor-pointer transition ${
          dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
      >
        <Upload size={24} className="mx-auto mb-2 text-slate-400" />
        <p className="text-sm font-medium text-slate-600">Drop CSV file here or click to browse</p>
        <p className="text-xs text-slate-400 mt-1">Requires CBC data with labels</p>
        <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
      </div>

      {/* Status messages */}
      {status === 'uploading' && (
        <div className="flex items-center gap-2 text-sm text-indigo-600">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Uploading dataset...
        </div>
      )}
      {status === 'training' && (
        <div className="flex items-center gap-2 text-sm text-indigo-600">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Training model...
        </div>
      )}
      {status === 'approved' && (
        <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
          <CheckCircle size={15} />
          Model approved and deployed successfully.
        </div>
      )}
      {status === 'rolled_back' && (
        <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2">
          <RotateCcw size={15} />
          Rolled back to previous model.
        </div>
      )}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}

      {/* Metrics */}
      {metrics && (
        <div className="bg-white rounded border border-slate-200 p-4 space-y-3">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">New Model Metrics</p>
          <MetricBar label="Accuracy" value={metrics.accuracy} />
          <MetricBar label="Precision" value={metrics.precision_score} />
          <MetricBar label="Recall" value={metrics.recall} />
          <MetricBar label="F1 Score" value={metrics.f1_score} />
        </div>
      )}

      {/* Approve / Rollback */}
      {status === 'pending_approval' && (
        <div className="flex gap-3">
          <button
            onClick={handleApprove}
            className="flex-1 flex items-center justify-center gap-2 text-white font-semibold py-2 rounded text-sm transition"
            style={{ backgroundColor: '#6366f1' }}
          >
            <CheckCircle size={14} />
            Approve
          </button>
          <button
            onClick={handleRollback}
            className="flex-1 flex items-center justify-center gap-2 font-semibold py-2 rounded text-sm transition border border-slate-200 text-slate-600 hover:bg-slate-50"
          >
            <RotateCcw size={14} />
            Rollback
          </button>
        </div>
      )}
    </div>
  );
}
