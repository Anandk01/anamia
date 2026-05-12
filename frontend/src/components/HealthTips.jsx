/**
 * HealthTips.jsx
 * Numbered list with left accent bar colored by severity.
 */

const SEVERITY_COLORS = {
  None:     '#10b981',
  Mild:     '#f59e0b',
  Moderate: '#f97316',
  Severe:   '#ef4444',
};

export default function HealthTips({ tips = [], severity = 'None' }) {
  const accentColor = SEVERITY_COLORS[severity] || SEVERITY_COLORS['None'];

  if (!tips.length) return null;

  return (
    <div className="bg-white rounded border border-slate-200 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-slate-100">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Health Tips</span>
      </div>
      <ul className="divide-y divide-slate-50">
        {tips.map((tip, idx) => (
          <li key={idx} className="flex items-start gap-3 px-4 py-2 hover:bg-slate-50 transition leading-snug">
            <div
              className="w-1 self-stretch rounded-full flex-shrink-0 mt-0.5"
              style={{ backgroundColor: accentColor, minHeight: '16px' }}
            />
            <span className="text-xs font-semibold text-slate-400 flex-shrink-0 mt-0.5 w-4">{idx + 1}.</span>
            <span className="text-sm text-slate-700 leading-snug">{tip}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
