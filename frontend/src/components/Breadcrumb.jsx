import React from 'react';
import { ChevronRight } from 'lucide-react';

export default function Breadcrumb({ items = [] }) {
  return (
    <nav className="flex items-center gap-1 text-xs text-slate-500" aria-label="Breadcrumb">
      {items.map((item, idx) => (
        <React.Fragment key={idx}>
          {idx > 0 && <ChevronRight size={10} className="text-slate-300" />}
          <span className={idx === items.length - 1 ? 'text-slate-700 font-medium' : 'hover:text-slate-700 cursor-pointer'}>
            {item}
          </span>
        </React.Fragment>
      ))}
    </nav>
  );
}
