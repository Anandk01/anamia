/**
 * DietRecommendations.jsx
 * Collapsible section with food items, vegan filter.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export default function DietRecommendations({ items = [], veganOnly = false }) {
  const [open, setOpen] = useState(true);

  const filtered = veganOnly ? items.filter((i) => i.is_vegan) : items;

  return (
    <div className="bg-white rounded border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition"
      >
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Diet Recommendations
          {veganOnly && (
            <span className="ml-2 text-emerald-600 normal-case font-medium">🌱 Vegan only</span>
          )}
        </span>
        {open ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
      </button>

      {open && (
        <div className="divide-y divide-slate-50">
          {filtered.length === 0 ? (
            <p className="px-4 py-3 text-sm text-slate-400">No recommendations available.</p>
          ) : (
            filtered.map((item, idx) => (
              <div key={idx} className="flex items-start gap-2 px-4 py-2 hover:bg-slate-50 transition">
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold text-slate-700">{item.name}</span>
                  {item.rationale && (
                    <span className="text-sm text-slate-400 ml-2">{item.rationale}</span>
                  )}
                </div>
                {item.is_vegan && (
                  <span className="text-xs text-emerald-600 flex-shrink-0 mt-0.5" title="Vegan">🌱</span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
