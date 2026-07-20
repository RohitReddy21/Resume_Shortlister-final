import { clsx } from 'clsx';

interface ListCardProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}

export function ListCard({ title, subtitle, children }: ListCardProps) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
      <div className="border-b border-slate-800 px-6 py-5">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
      </div>
      <div className={clsx('space-y-3 p-6')}>{children}</div>
    </div>
  );
}
