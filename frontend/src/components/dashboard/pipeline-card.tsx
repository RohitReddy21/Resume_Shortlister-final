interface PipelineCardProps {
  stage: string;
  count: number;
  progress: number;
}

export function PipelineCard({ stage, count, progress }: PipelineCardProps) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-white">{stage}</p>
        <p className="rounded-full bg-slate-950 px-3 py-1 text-xs text-slate-300">{count} candidates</p>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-950">
        <div className="h-full rounded-full bg-cyan-500" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-3 text-sm text-slate-400">{progress}% complete</p>
    </div>
  );
}
