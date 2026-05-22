import React from 'react';

export default function LoadingSkeleton({ variant = 'card', count = 1 }) {
  const items = Array.from({ length: count });

  if (variant === 'card') {
    return (
      <div className="space-y-4">
        {items.map((_, i) => (
          <div key={i} className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded-lg h-32 w-full" />
        ))}
      </div>
    );
  }

  if (variant === 'table-row') {
    return (
      <div className="space-y-2">
        {items.map((_, i) => (
          <div key={i} className="animate-pulse flex gap-4 items-center">
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4" />
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/5" />
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/6" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'text') {
    return (
      <div className="space-y-2 animate-pulse">
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full" />
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-4/5" />
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/5" />
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded-lg h-48 w-full" />
    );
  }

  return <div className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded-lg h-24 w-full" />;
}
