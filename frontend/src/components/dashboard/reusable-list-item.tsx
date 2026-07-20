interface ReusableListItemProps {
  title: string;
  subtitle: string;
  badge: string;
  meta: string;
}

export function ReusableListItem({ title, subtitle, badge, meta }: ReusableListItemProps) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/95 p-4 transition hover:border-cyan-400">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium text-white">{title}</p>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs uppercase tracking-[0.25em] text-slate-300">{badge}</span>
      </div>
      <p className="mt-3 text-sm text-slate-500">{meta}</p>
    </div>
  );
}
