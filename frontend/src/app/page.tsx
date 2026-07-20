import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-6 py-12">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-900/80 p-10 shadow-2xl">
        <p className="text-sm uppercase tracking-[0.35em] text-cyan-400">ResumeParser.AI</p>
        <h1 className="mt-4 text-4xl font-semibold text-white">Secure hiring workflows start with trusted authentication.</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300">
          Built for admins, recruiters, hiring managers, and candidates with JWTs, refresh tokens, Google OAuth, and role-based access control.
        </p>
        <div className="mt-8 flex flex-wrap gap-4">
          <Link href="/login" className="rounded-full bg-cyan-500 px-6 py-3 font-medium text-slate-950 transition hover:bg-cyan-400">Sign in</Link>
          <Link href="/signup" className="rounded-full border border-slate-700 px-6 py-3 font-medium text-white transition hover:border-cyan-400">Create account</Link>
        </div>
      </div>
    </main>
  );
}
