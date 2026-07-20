"use client";

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useState } from 'react';
import { resetPassword } from '@/lib/api';

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const response = await resetPassword(token, password);
      setMessage((response as { message?: string }).message ?? 'Password updated');
      router.push('/login');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset password');
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
        <h1 className="text-3xl font-semibold text-white">Reset password</h1>
        <p className="mt-2 text-sm text-slate-400">Choose a strong new password for your account.</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {error ? <div className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div> : null}
          {message ? <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">{message}</div> : null}
          <div>
            <label className="mb-2 block text-sm text-slate-300">New password</label>
            <input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <button className="w-full rounded-full bg-cyan-500 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-400" type="submit">Update password</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400"><Link href="/login" className="text-cyan-300">Back to sign in</Link></p>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">Loading…</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
