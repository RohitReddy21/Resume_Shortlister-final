"use client";

import { FormEvent, useState } from 'react';
import { AlertCircle, CheckCircle2, Gauge, Lightbulb, Loader2, Target } from 'lucide-react';
import { getATSScore, type ATSScoreResponse } from '@/lib/api';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const componentLabels: Record<string, string> = {
  skills: 'Skills',
  experience: 'Experience',
  education: 'Education',
  keywords: 'Keywords',
};

const componentOrder = ['skills', 'experience', 'education', 'keywords'];

function clampPercent(value: number) {
  return Math.min(100, Math.max(0, value));
}

function formatPercent(value: number) {
  return `${Math.round(clampPercent(value * 100))}%`;
}

function formatScore(value: number) {
  return `${Math.round(clampPercent(value))}%`;
}

function formatSkill(skill: string) {
  return skill
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function scoreTone(score: number) {
  if (score >= 80) {
    return {
      text: 'text-emerald-300',
      bg: 'bg-emerald-400',
      border: 'border-emerald-400/40',
      label: 'Strong match',
    };
  }
  if (score >= 60) {
    return {
      text: 'text-cyan-300',
      bg: 'bg-cyan-400',
      border: 'border-cyan-400/40',
      label: 'Review fit',
    };
  }
  return {
    text: 'text-amber-300',
    bg: 'bg-amber-400',
    border: 'border-amber-400/40',
    label: 'Needs work',
  };
}

function sortComponentEntries(scores: Record<string, number>) {
  return Object.entries(scores).sort(([left], [right]) => {
    const leftIndex = componentOrder.indexOf(left);
    const rightIndex = componentOrder.indexOf(right);
    return (leftIndex === -1 ? componentOrder.length : leftIndex) - (rightIndex === -1 ? componentOrder.length : rightIndex);
  });
}

function SkillChips({ items, empty, tone }: { items: string[]; empty: string; tone: 'matched' | 'missing' }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">{empty}</p>;
  }

  const className =
    tone === 'matched'
      ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
      : 'border-amber-400/30 bg-amber-400/10 text-amber-200';

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className={`rounded-full border px-3 py-1 text-xs font-medium ${className}`}>
          {formatSkill(item)}
        </span>
      ))}
    </div>
  );
}

function InsightList({
  icon,
  items,
  title,
  empty,
}: {
  icon: React.ReactNode;
  items: string[];
  title: string;
  empty: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
        {icon}
        <h4>{title}</h4>
      </div>
      {items.length ? (
        <ul className="space-y-2 text-sm text-slate-300">
          {items.map((item) => (
            <li key={item} className="leading-6">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{empty}</p>
      )}
    </div>
  );
}

function ScoreResults({ score }: { score: ATSScoreResponse }) {
  const tone = scoreTone(score.score_percentage);
  const components = sortComponentEntries(score.component_scores);

  return (
    <div className="space-y-6">
      <div className={`rounded-2xl border ${tone.border} bg-slate-950/70 p-5`}>
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Match score</p>
            <div className="mt-3 flex items-end gap-3">
              <span className={`text-6xl font-semibold leading-none ${tone.text}`}>{formatScore(score.score_percentage)}</span>
              <span className="pb-2 text-sm font-medium text-slate-400">{tone.label}</span>
            </div>
          </div>
          <div className="text-sm text-slate-400 md:text-right">
            <p>Resume ID: <span className="font-mono text-slate-200">{score.resume_id}</span></p>
            <p className="mt-1">Job ID: <span className="font-mono text-slate-200">{score.job_id}</span></p>
          </div>
        </div>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-900">
          <div className={`h-full rounded-full ${tone.bg}`} style={{ width: `${clampPercent(score.score_percentage)}%` }} />
        </div>
        {score.explanation ? <p className="mt-4 text-sm text-slate-300">{score.explanation}</p> : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {components.map(([key, value]) => {
          const width = clampPercent(value * 100);
          return (
            <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{componentLabels[key] ?? key}</p>
                  <p className="mt-1 text-xs text-slate-500">Weight {formatPercent(score.weights[key] ?? 0)}</p>
                </div>
                <p className="text-lg font-semibold text-cyan-300">{formatPercent(value)}</p>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-900">
                <div className="h-full rounded-full bg-cyan-500" style={{ width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <CheckCircle2 className="h-4 w-4 text-emerald-300" />
            <h4>Matched skills</h4>
          </div>
          <SkillChips items={score.matched_skills} empty="No matched skills returned." tone="matched" />
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <AlertCircle className="h-4 w-4 text-amber-300" />
            <h4>Missing skills</h4>
          </div>
          <SkillChips items={score.missing_skills} empty="No missing skills returned." tone="missing" />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <InsightList
          icon={<CheckCircle2 className="h-4 w-4 text-emerald-300" />}
          title="Strengths"
          items={score.strengths}
          empty="No strengths returned."
        />
        <InsightList
          icon={<AlertCircle className="h-4 w-4 text-amber-300" />}
          title="Weaknesses"
          items={score.weaknesses}
          empty="No weaknesses returned."
        />
        <InsightList
          icon={<Lightbulb className="h-4 w-4 text-cyan-300" />}
          title="Recommendations"
          items={score.recommendations}
          empty="No recommendations returned."
        />
      </div>
    </div>
  );
}

export function ATSScorePanel() {
  const [resumeId, setResumeId] = useState('');
  const [jobId, setJobId] = useState('');
  const [score, setScore] = useState<ATSScoreResponse | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedResumeId = resumeId.trim();
    const trimmedJobId = jobId.trim();

    if (!trimmedResumeId || !trimmedJobId) {
      setError('Enter both a parsed resume ID and a job ID.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await getATSScore(trimmedResumeId, trimmedJobId);
      setScore(response);
    } catch (err) {
      setScore(null);
      setError(err instanceof Error ? err.message : 'Could not load ATS score.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
      <div className="border-b border-slate-800 px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-slate-400">ATS scoring</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Resume to job match</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Score any parsed resume against a job opening and review the fit signals recruiters need before shortlisting.
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">
            <Gauge className="h-4 w-4" />
            Live endpoint
          </div>
        </div>
      </div>

      <div className="space-y-6 p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <div>
            <Label htmlFor="ats-resume-id">Parsed resume ID</Label>
            <Input
              id="ats-resume-id"
              value={resumeId}
              onChange={(event) => setResumeId(event.target.value)}
              placeholder="e.g. 1f9c..."
              autoComplete="off"
            />
          </div>
          <div>
            <Label htmlFor="ats-job-id">Job ID</Label>
            <Input
              id="ats-job-id"
              value={jobId}
              onChange={(event) => setJobId(event.target.value)}
              placeholder="e.g. 8a23..."
              autoComplete="off"
            />
          </div>
          <Button type="submit" className="h-12 px-5" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Scoring
              </>
            ) : (
              <>
                <Target className="mr-2 h-4 w-4" />
                Score match
              </>
            )}
          </Button>
        </form>

        {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}

        {score ? (
          <ScoreResults score={score} />
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 px-5 py-8 text-center">
            <Target className="mx-auto h-8 w-8 text-slate-500" />
            <h3 className="mt-3 text-base font-semibold text-white">No score loaded</h3>
            <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
              Submit a parsed resume ID and job ID to view the ATS score, component weights, missing keywords, and recommended resume improvements.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
