import Link from 'next/link';
import type { ReactNode } from 'react';

interface AuthShellProps {
  title: string;
  description: string;
  children: ReactNode;
}

export function AuthShell({ title, description, children }: AuthShellProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
        <p className="text-sm uppercase tracking-[0.35em] text-cyan-400">ResumeParser.AI</p>
        <h1 className="mt-4 text-3xl font-semibold text-white">{title}</h1>
        <p className="mt-2 text-sm text-slate-400">{description}</p>
        {children}
        <p className="mt-6 text-center text-sm text-slate-400">
          <Link href="/login" className="text-cyan-300">Back to sign in</Link>
        </p>
      </div>
    </main>
  );
}
