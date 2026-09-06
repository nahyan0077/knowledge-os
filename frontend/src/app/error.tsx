'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-950 text-zinc-100 p-8">
      <div className="h-14 w-14 rounded-full bg-red-500/10 flex items-center justify-center mb-5">
        <AlertTriangle className="h-7 w-7 text-red-400" />
      </div>
      <h1 className="text-xl font-bold text-zinc-100 mb-2">Application Error</h1>
      <p className="text-sm text-zinc-400 mb-2 max-w-md text-center">
        An unexpected error occurred in the application.
      </p>
      {error.digest && (
        <p className="text-xs text-zinc-500 mb-6 font-mono">Error ID: {error.digest}</p>
      )}
      <button
        onClick={reset}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 hover:bg-zinc-700 transition-colors text-sm font-medium cursor-pointer"
      >
        <RefreshCw className="h-4 w-4" />
        Reload page
      </button>
    </div>
  );
}
