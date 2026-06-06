'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return (
    <div className="flex-1 flex items-center justify-center bg-zinc-950 text-zinc-100">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
        <span className="text-xs text-zinc-500">Redirecting to workspace...</span>
      </div>
    </div>
  );
}
