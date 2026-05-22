import React, { useState, useEffect } from 'react';
import client from '../api/client';

const MODELS = ['Random Forest', 'Gradient Boosting', 'XGBoost', 'LightGBM'];
const METRICS = ['accuracy', 'precision', 'recall', 'f1', 'auc_roc'];
const METRIC_LABELS = { accuracy: 'Accuracy', precision: 'Precision', recall: 'Recall', f1: 'F1', auc_roc: 'AUC-ROC' };

function ConfusionMatrix({ matrix }) {
  if (!matrix || !matrix.length) return <p className="text-sm text-slate-400">No confusion matrix data</p>;
  const max = Math.max(...matrix.flat());
  return (
    <div className="inline-grid gap-1" style={{ gridTemplateColumns: `repeat(${matrix[0].length}, 48px)` }}>
      {matrix.map((row, i) =>
        row.map((val, j) => {
          const intensity = max > 0 ? val / max : 0;
          return (
            <div
              key={`${i}-${j}`}
              className="w-12 h-12 flex items-center justify-center text-xs font-bold rounded"
              style={{
                backgroundColor: `rgba(99, 102, 241, ${0.1 + intensity * 0.8})`,
                color: intensity > 0.5 ? '#fff' : '#334155',
              }}
            >
              {val}
            </div>
          );
        })
      )}
    </div>
  );
}

export default function ModelComparison() {
  const [metrics, setMetrics] = useState([]);
  const [activeModel, setActiveModel] = useState(MODELS[0]);

  useEffect(() => {
    client.get('/api/retrain/metrics')
      .then(res => setMetrics(res.data?.models || []))
      .catch(() => setMetrics([]));
  }, []);

  // Find best value per metric
  const bestValues = {};
  METRICS.forEach(m => {
    let best = -1;
    metrics.forEach(model => {
      if ((model[m] || 0) > best) best = model[m] || 0;
    });
    bestValues[m] = best;
  });

  const activeMetrics = metrics.find(m => m.name === activeModel);

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-slate-800">Model Comparison</h2>

      {/* Metrics table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">Model</th>
              {METRICS.map(m => (
                <th key={m} className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">{METRIC_LABELS[m]}</th>
              ))}
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase">Trained At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(metrics.length > 0 ? metrics : MODELS.map(name => ({ name }))).map(model => (
              <tr key={model.name} className="hover:bg-slate-50">
                <td className="px-4 py-2.5 font-medium text-slate-700">{model.name}</td>
                {METRICS.map(m => {
                  const val = model[m];
                  const isBest = val != null && val === bestValues[m] && metrics.length > 1;
                  return (
                    <td key={m} className={`px-4 py-2.5 ${isBest ? 'bg-green-100 text-green-800 font-bold' : 'text-slate-600'}`}>
                      {val != null ? val.toFixed(4) : '—'}
                    </td>
                  );
                })}
                <td className="px-4 py-2.5 text-xs text-slate-400">{model.trained_at || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Confusion matrix */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Confusion Matrix</p>
        <div className="flex gap-2 mb-4">
          {MODELS.map(m => (
            <button
              key={m}
              onClick={() => setActiveModel(m)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                activeModel === m ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <ConfusionMatrix matrix={activeMetrics?.confusion_matrix} />
      </div>
    </div>
  );
}
