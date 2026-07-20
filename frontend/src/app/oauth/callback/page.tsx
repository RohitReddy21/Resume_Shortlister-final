"use client";

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect } from 'react';
import { saveTokens } from '@/lib/auth';

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');
    if (accessToken && refreshToken) {
      saveTokens({ access_token: accessToken, refresh_token: refreshToken });
      router.push('/dashboard');
    }
  }, [router, searchParams]);

  return <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">Completing sign-in…</div>;
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">Loading…</div>}>
      <OAuthCallbackContent />
    </Suspense>
  );
}
