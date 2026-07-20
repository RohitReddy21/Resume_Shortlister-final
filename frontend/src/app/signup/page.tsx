"use client";

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';
import { signup } from '@/lib/api';

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('Candidate');
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await signup({ email, password, full_name: fullName, role });
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create account');
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
        <h1 className="text-3xl font-semibold text-white">Create your account</h1>
        <p className="mt-2 text-sm text-slate-400">Join ResumeParser.AI as a recruiter, hiring manager, or candidate.</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {error ? <div className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div> : null}
          <div>
            <label className="mb-2 block text-sm text-slate-300">Full name</label>
            <input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Email</label>
            <input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Password</label>
            <input className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Role</label>
            <select className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0" value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="Candidate">Candidate</option>
              <option value="Recruiter">Recruiter</option>
              <option value="Hiring Manager">Hiring Manager</option>
              <option value="Admin">Admin</option>
            </select>
          </div>
          <button className="w-full rounded-full bg-cyan-500 px-4 py-3 font-medium text-slate-950 transition hover:bg-cyan-400" type="submit">Create account</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400">Already have an account? <Link href="/login" className="text-cyan-300">Sign in</Link></p>
      </div>
    </main>
  );
}
