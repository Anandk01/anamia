/**
 * PredictionResult.jsx
 * Displays anemia prediction with severity badge, type chip,
 * confidence bar, SHAP explanation table, and AI-generated clinical report.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const SEVERITY_CONFIG = {
  None:     { border: '#10b981', badge: 'bg-emerald-100 text-emerald-700', label: 'None' },
  Mild:     { border: '#f59e0b', badge: 'bg-amber-100 text-amber-700',     label: 'Mild' },
  Moderate: { border: '#f97316', badge: 'bg-orange-100 text-orange-700',   label: 'Moderate' },
  Severe:   { border: '#ef4444', badge: 'bg-red-100 text-red-700',         label: 'Severe' },
};

function getSeverityConfig(severity) {
  return SEVERITY_CONFIG[severity] || SEVERITY_CONFIG['None'];
}

export default function PredictionResult({ result }) {
  if (!result) return null;
  const [showAiReport, setShowAiReport] = useState(true);

  const {
    anemia_detected,
    severity_level = 'None',
    anemia_type = 'N/A',
    anemia_confidence,
    confidence,
    explanation = [],
    ai_report,
    ai_sources = [],
  } = result;

  const conf = anemia_confidence ?? confidence ?? 0;
  const sevConfig = getSeverityConfig(severity_level);
  const isAnemia = anemia_detected === 1 || anemia_detected === true;

  const statusBorderColor = isAnemia ? '#ef4444' : '#10b981';
  const statusBg = isAnemia ? '#fef2f2' : '#f0fdf4';
  const statusText = isAnemia ? '#dc2626' : '#16a34a';
  const statusLabel = isAnemia ? 'Anemia Detected' : 'No Anemia';

  const topExplanations = Array.isArray(explanation) ? explanation.slice(0, 3) : [];
  const maxShap = Math.max(...topExplanations.map((e) => Math.abs(e.shap_value || 0)), 0.001);

  return (
    <div className="space-y-4">
      {/* Status bar */}
      <div
        className="rounded border-l-4 px-4 py-3 flex items-center justify-between"
        style={{ borderLeftColor: statusBorderColor, backgroundColor: statusBg }}
        data-testid="prediction-status-bar"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: statusText }}>
            Prediction Result
          </p>
          <p className="text-lg font-bold mt-0.5" style={{ color: statusText }}>
            {statusLabel}
          </p>
        </div>
        {/* Severity badge */}
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${sevConfig.badge}`}
          data-testid="severity-badge"
        >
          {sevConfig.label}
        </span>
      </div>

      {/* Type + Confidence */}
      <div className="bg-white rounded border border-slate-200 px-4 py-3 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Anemia Type</span>
          <span className="text-sm font-medium text-slate-700 bg-slate-100 px-2.5 py-0.5 rounded-full">
            {anemia_type}
          </span>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Confidence</span>
            <span className="text-xs font-bold text-slate-700">{(conf * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${conf * 100}%`, backgroundColor: sevConfig.border }}
            />
          </div>
        </div>
      </div>

      {/* SHAP Explanation Table */}
      {topExplanations.length > 0 && (
        <div className="bg-white rounded border border-slate-200 overflow-hidden">
          <div className="px-4 py-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Top Feature Explanations (SHAP)
            </span>
          </div>
          <table className="w-full text-sm" data-testid="shap-table">
            <thead>
              <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                <th className="px-4 py-2 text-left">Feature</th>
                <th className="px-4 py-2 text-left">Direction</th>
                <th className="px-4 py-2 text-left">Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {topExplanations.map((item, idx) => {
                const pct = Math.round((Math.abs(item.shap_value || 0) / maxShap) * 100);
                const barColor = item.direction === 'High' ? '#ef4444' : '#6366f1';
                return (
                  <tr key={idx} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-2 font-medium text-slate-700">{item.feature}</td>
                    <td className="px-4 py-2 text-slate-500">{item.direction}</td>
                    <td className="px-4 py-2 w-32">
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: barColor }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* AI Clinical Report */}
      {ai_report && (
        <div className="bg-white rounded border border-indigo-200 overflow-hidden">
          <button
            onClick={() => setShowAiReport((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2.5 border-b border-indigo-100 hover:bg-indigo-50 transition"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-indigo-600 uppercase tracking-wide">✨ AI Clinical Report</span>
              <span className="text-xs text-slate-400 font-normal">Powered by Gemini · WHO & NHLBI sources</span>
            </div>
            {showAiReport ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
          </button>
          {showAiReport && (
            <div className="px-4 py-3 space-y-2">
              <div
                className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap"
                style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}
              >
                {ai_report}
              </div>
              {ai_sources.length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Sources</p>
                  <div className="space-y-0.5">
                    {ai_sources.map((src, i) => (
                      <a
                        key={i}
                        href={src}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 transition"
                      >
                        <ExternalLink size={10} />
                        {src.replace('https://', '').split('/')[0]}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
