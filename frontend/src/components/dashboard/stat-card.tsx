import { clsx } from 'clsx';

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  caption?: string;
  icon: React.ReactNode;
}

export function StatCard({ label, value, delta, caption, icon }: StatCardProps) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 shadow-sm shadow-slate-950/20 transition hover:border-cyan-400">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">{label}</p>
          <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
        </div>
        <div className="rounded-2xl bg-slate-950 p-3 text-cyan-300">{icon}</div>
      </div>
      {delta ? (
        <p className={clsx('mt-4 text-sm', delta.startsWith('+') ? 'text-emerald-400' : 'text-rose-400')}>{delta} vs last week</p>
      ) : (
        <p className="mt-4 text-sm text-slate-500">{caption ?? 'Live data'}</p>
      )}
    </div>
  );
}
