import React from 'react';

export default function StatusFooter() {
  return (
    <div className="h-6 bg-slate-100 border-t border-slate-200 flex items-center justify-between px-4 text-xs text-slate-500 flex-shrink-0">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          Connected
        </span>
        <span>English</span>
      </div>
      <div className="flex items-center gap-3">
        <span>Last sync: just now</span>
        <span>v2.0.0</span>
      </div>
    </div>
  );
}
