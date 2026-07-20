"use client";

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Briefcase, CalendarDays, ChevronDown, Command, Loader2, Users } from 'lucide-react';
import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { StatCard } from '@/components/dashboard/stat-card';
import { ListCard } from '@/components/dashboard/list-card';
import { PipelineCard } from '@/components/dashboard/pipeline-card';
import { ReusableListItem } from '@/components/dashboard/reusable-list-item';
import { ATSScorePanel } from '@/components/dashboard/ats-score-panel';
import { getDashboardSummary, type DashboardSummary } from '@/lib/api';

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/70 p-5 text-sm text-slate-500">
      {label}
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load dashboard summary.'))
      .finally(() => setLoading(false));
  }, []);

  const statData = useMemo(
    () => [
      { label: 'Candidates', value: String(summary?.stats.candidates ?? 0), caption: 'Profiles in database', icon: <Users className="h-5 w-5" /> },
      { label: 'Open roles', value: String(summary?.stats.open_jobs ?? 0), caption: 'Jobs not closed', icon: <Briefcase className="h-5 w-5" /> },
      { label: 'Applications', value: String(summary?.stats.applications ?? 0), caption: 'Real pipeline records', icon: <Command className="h-5 w-5" /> },
      { label: 'Shortlisted', value: String(summary?.stats.shortlisted ?? 0), caption: 'ATS score met threshold', icon: <CalendarDays className="h-5 w-5" /> },
    ],
    [summary],
  );

  return (
    <DashboardFrame title="Hiring pipeline overview">
      {loading ? (
        <div className="flex items-center gap-2 rounded-3xl border border-slate-800 bg-slate-900/90 p-5 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
          Loading live dashboard data
        </div>
      ) : null}

      {error ? (
        <div className="flex items-center gap-2 rounded-3xl border border-rose-400/30 bg-rose-950/30 p-5 text-sm text-rose-100">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        {statData.map((stat) => (
          <StatCard key={stat.label} label={stat.label} value={stat.value} caption={stat.caption} icon={stat.icon} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.65fr)_minmax(0,0.35fr)]">
        <div className="space-y-6">
          <ListCard title="Recent candidates" subtitle="Latest scored applications">
            <div className="space-y-4">
              {summary?.recent_candidates.length ? (
                summary.recent_candidates.map((candidate) => (
                  <ReusableListItem key={`${candidate.title}-${candidate.meta}`} {...candidate} />
                ))
              ) : (
                <EmptyState label="No applications yet. Upload resumes and score them against a job to populate this list." />
              )}
            </div>
          </ListCard>
          <ListCard title="Hiring pipeline" subtitle="Live application stages">
            <div className="space-y-4">
              {summary?.pipeline.length ? (
                summary.pipeline.map((stage) => (
                  <PipelineCard key={stage.stage} {...stage} />
                ))
              ) : (
                <EmptyState label="No pipeline records yet." />
              )}
            </div>
          </ListCard>
          <ATSScorePanel />
        </div>

        <div className="space-y-6">
          <ListCard title="Recent jobs" subtitle="Open roles from the backend">
            <div className="space-y-4">
              {summary?.recent_jobs.length ? (
                summary.recent_jobs.map((job) => (
                  <ReusableListItem key={`${job.title}-${job.meta}`} {...job} />
                ))
              ) : (
                <EmptyState label="No jobs found. Create a job to start scoring resumes." />
              )}
            </div>
          </ListCard>
          <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Shortcuts</p>
                <h2 className="mt-2 text-lg font-semibold text-white">Quick actions</h2>
              </div>
              <ChevronDown className="h-5 w-5 text-slate-400" />
            </div>
            <div className="mt-6 grid gap-3">
              <Link href="/dashboard/jobs" className="rounded-3xl border border-slate-800 bg-slate-950 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-cyan-400">
                Post a new job
              </Link>
              <Link href="/dashboard/candidates" className="rounded-3xl border border-slate-800 bg-slate-950 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-cyan-400">
                Score and shortlist resumes
              </Link>
              <Link href="/dashboard/pipeline" className="rounded-3xl border border-slate-800 bg-slate-950 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-cyan-400">
                Review candidate pipeline
              </Link>
            </div>
          </div>
        </div>
      </div>
    </DashboardFrame>
  );
}
