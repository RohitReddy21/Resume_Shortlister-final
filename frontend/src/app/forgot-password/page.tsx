"use client";

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { forgotPassword } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const response = await forgotPassword(email);
      setMessage((response as { message?: string }).message ?? 'Check your inbox if the account exists.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to request reset');
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
        <h1 className="text-3xl font-semibold text-white">Forgot password?</h1>
        <p className="mt-2 text-sm text-slate-400">We will send a reset link to the email address on file.</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {error ? <div className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div> : null}
          {message ? <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">{message}</div> : null}
          <div>
            <label className="mb-2 block text-sm text-slate-300">Email</label>
            <input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <button className="w-full rounded-full bg-cyan-500 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-400" type="submit">Send reset link</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400"><Link href="/login" className="text-cyan-300">Back to sign in</Link></p>
      </div>
    </main>
  );
}
