/**
 * CBCForm.jsx
 * Compact 2-column grid of 8 CBC inputs with real-time validation,
 * OCR upload support, and confidence badges.
 */

import React, { useState, useRef } from 'react';
import { Paperclip } from 'lucide-react';
import client from '../api/client.js';

const FIELDS = [
  { key: 'RBC',  label: 'RBC',  unit: 'M/µL',  ref: '4.0–5.5',  min: 0, max: 10, step: '0.01' },
  { key: 'MCV',  label: 'MCV',  unit: 'fL',    ref: '80–100',   min: 0, max: 200, step: '0.1' },
  { key: 'MCH',  label: 'MCH',  unit: 'pg',    ref: '27–33',    min: 0, max: 60, step: '0.1' },
  { key: 'MCHC', label: 'MCHC', unit: 'g/dL',  ref: '32–36',    min: 0, max: 50, step: '0.1' },
  { key: 'RDW',  label: 'RDW',  unit: '%',     ref: '11.5–14.5',min: 0, max: 30, step: '0.1' },
  { key: 'TLC',  label: 'TLC',  unit: 'K/µL',  ref: '4.0–11.0', min: 0, max: 50, step: '0.01' },
  { key: 'PLT',  label: 'PLT',  unit: 'K/µL',  ref: '150–400',  min: 0, max: 1500, step: '1' },
  { key: 'HGB',  label: 'HGB',  unit: 'g/dL',  ref: '12.0–17.0',min: 0, max: 25, step: '0.1' },
];

const EMPTY = Object.fromEntries(FIELDS.map((f) => [f.key, '']));

function confidenceBadge(conf) {
  if (!conf) return null;
  if (conf === 'High' || conf >= 0.8) return { label: 'High', cls: 'bg-emerald-100 text-emerald-700' };
  if (conf === 'Medium' || conf === 'Med' || conf >= 0.5) return { label: 'Med', cls: 'bg-amber-100 text-amber-700' };
  return { label: 'Low', cls: 'bg-red-100 text-red-700' };
}

function validateField(key, value) {
  if (value === '' || value === undefined) return 'required';
  const num = parseFloat(value);
  if (isNaN(num)) return 'invalid';
  if (num < 0) return 'negative';
  return null;
}

export default function CBCForm({ onSubmit, loading, ocrValues, ocrConfidence }) {
  const [form, setForm] = useState(EMPTY);
  const [touched, setTouched] = useState({});
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState(null);
  const [confidence, setConfidence] = useState({});
  const fileRef = useRef(null);

  // Merge OCR values when they arrive
  const displayValues = { ...form };
  if (ocrValues) {
    FIELDS.forEach(({ key }) => {
      if (ocrValues[key.toLowerCase()] !== undefined && form[key] === '') {
        displayValues[key] = String(ocrValues[key.toLowerCase()]);
      }
    });
  }

  function handleChange(key, value) {
    const field = FIELDS.find(f => f.key === key);
    if (field && value !== '') {
      // Prevent negative numbers
      if (value.startsWith('-')) return;

      const decimals = field.step === '0.01' ? 2 : field.step === '0.1' ? 1 : 0;
      const parts = value.split('.');
      
      // Limit integer digits
      const maxIntDigits = String(field.max).length;
      if (parts[0].length > maxIntDigits) {
        return;
      }

      // Enforce decimal places
      if (parts.length > 1 && parts[1].length > decimals) {
        value = parts[0] + '.' + parts[1].slice(0, decimals);
      }

      // Block values greater than max
      const numValue = parseFloat(value);
      if (!isNaN(numValue) && numValue > field.max) {
        return;
      }
    }
    setForm((prev) => ({ ...prev, [key]: value }));
    setTouched((prev) => ({ ...prev, [key]: true }));
  }

  function handleBlur(key) {
    setTouched((prev) => ({ ...prev, [key]: true }));
  }

  async function handleOcrUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setOcrLoading(true);
    setOcrError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await client.post('/api/ocr/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      const vals = res.data?.values || {};
      const confs = res.data?.confidence || {};
      const warnings = res.data?.warnings || [];
      
      if (warnings && warnings.length > 0 && (!vals || Object.keys(vals).length === 0)) {
        setOcrError(warnings[0]);
      } else if (warnings && warnings.length > 0) {
        console.warn('OCR Warnings:', warnings);
      }

      const newForm = { ...form };
      let matched = false;
      FIELDS.forEach(({ key }) => {
        if (vals && vals[key.toLowerCase()] !== undefined) {
          newForm[key] = String(vals[key.toLowerCase()]);
          matched = true;
        }
      });

      if (!matched && (!warnings || warnings.length === 0)) {
        setOcrError('Could not extract any CBC values from this file. Please ensure it is a clear lab report.');
      }

      setForm(newForm);
      setConfidence(confs);
    } catch (err) {
      console.error('OCR Error:', err);
      setOcrError(err.response?.data?.message || 'OCR upload failed.');
    } finally {
      setOcrLoading(false);
      e.target.value = '';
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    // Mark all touched
    const allTouched = Object.fromEntries(FIELDS.map((f) => [f.key, true]));
    setTouched(allTouched);

    const hasErrors = FIELDS.some((f) => validateField(f.key, displayValues[f.key]));
    if (hasErrors) return;

    const cbcData = Object.fromEntries(
      FIELDS.map((f) => [f.key, parseFloat(displayValues[f.key])])
    );
    onSubmit(cbcData);
  }

  const allValid = FIELDS.every((f) => !validateField(f.key, displayValues[f.key]));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* OCR upload row */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">CBC Parameters</span>
        <div className="flex items-center gap-2">
          {ocrError && <span className="text-xs text-red-500">{ocrError}</span>}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={ocrLoading}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600 transition disabled:opacity-50"
            title="Upload CBC report image for OCR"
          >
            <Paperclip size={13} />
            {ocrLoading ? 'Reading...' : 'OCR Upload'}
          </button>
          <input ref={fileRef} type="file" accept="image/*,.pdf" className="hidden" onChange={handleOcrUpload} />
        </div>
      </div>

      {/* 2-column grid */}
      <div className="grid grid-cols-2 gap-3">
        {FIELDS.map(({ key, label, unit, ref: refRange, step, min, max }) => {
          const val = displayValues[key];
          const err = touched[key] ? validateField(key, val) : null;
          const conf = confidence[key.toLowerCase()] || ocrConfidence?.[key.toLowerCase()];
          const badge = confidenceBadge(conf);

          const borderColor = err
            ? 'border-red-400 bg-red-50'
            : val && !err
            ? 'border-emerald-400 bg-emerald-50'
            : 'border-slate-200 bg-slate-50';

          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-600">
                  {label}
                  <span className="ml-1 text-slate-400 font-normal">({unit})</span>
                </label>
                {badge && (
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${badge.cls}`}>
                    {badge.label}
                  </span>
                )}
              </div>
              <input
                type="number"
                step={step || 'any'}
                min={min}
                max={max}
                value={val}
                onChange={(e) => handleChange(key, e.target.value)}
                onBlur={() => handleBlur(key)}
                placeholder={refRange}
                className={`w-full rounded border px-2.5 py-1.5 text-sm text-slate-800 placeholder-slate-300 focus:outline-none focus:ring-2 focus:border-transparent transition ${borderColor}`}
                data-testid={`cbc-input-${key.toLowerCase()}`}
              />
              <p className="text-xs text-slate-400 mt-0.5">Ref: {refRange}</p>
              {err === 'required' && <p className="text-xs text-red-500 mt-0.5" data-testid={`error-${key.toLowerCase()}`}>Required</p>}
              {err === 'invalid' && <p className="text-xs text-red-500 mt-0.5" data-testid={`error-${key.toLowerCase()}`}>Invalid number</p>}
              {err === 'negative' && <p className="text-xs text-red-500 mt-0.5" data-testid={`error-${key.toLowerCase()}`}>Cannot be negative</p>}
            </div>
          );
        })}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full text-white font-semibold py-2 rounded text-sm transition disabled:opacity-60"
        style={{ backgroundColor: '#6366f1' }}
        data-testid="submit-cbc"
      >
        {loading ? 'Predicting...' : 'Submit CBC'}
      </button>
    </form>
  );
}
