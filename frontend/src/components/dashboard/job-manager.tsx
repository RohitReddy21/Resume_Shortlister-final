"use client";

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Briefcase, Edit3, Loader2, Plus, RefreshCw, Trash2, X } from 'lucide-react';
import { createJob, deleteJob, listJobs, updateJob, type Job, type JobPayload } from '@/lib/api';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function splitCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalNumber(value: string) {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function formatList(items?: string[] | null) {
  if (!items?.length) return 'No entries';
  return items.join(', ');
}

export function JobManager() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [skills, setSkills] = useState('');
  const [locations, setLocations] = useState('');
  const [remoteType, setRemoteType] = useState<JobPayload['remote_type']>('remote');
  const [status, setStatus] = useState<JobPayload['status']>('published');
  const [minSalary, setMinSalary] = useState('');
  const [maxSalary, setMaxSalary] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const publishedCount = useMemo(() => jobs.filter((job) => job.status === 'published').length, [jobs]);

  async function loadJobs() {
    setIsLoading(true);
    setError('');
    try {
      const payload = await listJobs();
      setJobs(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load jobs.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  function resetForm() {
    setEditingJobId(null);
    setTitle('');
    setDescription('');
    setSkills('');
    setLocations('');
    setRemoteType('remote');
    setStatus('published');
    setMinSalary('');
    setMaxSalary('');
    setCurrency('USD');
  }

  function handleEdit(job: Job) {
    setEditingJobId(job.id);
    setTitle(job.title ?? '');
    setDescription(job.description ?? '');
    setSkills((job.skills ?? []).join(', '));
    setLocations((job.locations ?? []).join(', '));
    setRemoteType(job.remote_type ?? 'remote');
    setStatus(job.status ?? 'published');
    setMinSalary(job.min_salary === null || job.min_salary === undefined ? '' : String(job.min_salary));
    setMaxSalary(job.max_salary === null || job.max_salary === undefined ? '' : String(job.max_salary));
    setCurrency(job.currency ?? 'USD');
    setError('');
    setSuccess('');
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSuccess('');

    const payload: JobPayload = {
      title: title.trim(),
      description: description.trim() || undefined,
      skills: splitCsv(skills),
      locations: splitCsv(locations),
      remote_type: remoteType,
      status,
      min_salary: optionalNumber(minSalary),
      max_salary: optionalNumber(maxSalary),
      currency: currency.trim() || undefined,
    };

    if (!payload.title) {
      setError('Job title is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingJobId) {
        const updated = await updateJob(editingJobId, payload);
        setJobs((current) => current.map((job) => (job.id === updated.id ? updated : job)));
        setSuccess(`Updated "${updated.title}".`);
      } else {
        const created = await createJob(payload);
        setJobs((current) => [created, ...current]);
        setSuccess(`Created "${created.title}". Use job ID ${created.id} for ATS scoring.`);
      }
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : editingJobId ? 'Unable to update job.' : 'Unable to create job.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(jobId: string) {
    setError('');
    setSuccess('');
    try {
      await deleteJob(jobId);
      setJobs((current) => current.filter((job) => job.id !== jobId));
      setSuccess('Job deleted.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete job.');
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
        <div className="border-b border-slate-800 px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Job intake</p>
              <h2 className="mt-2 text-xl font-semibold text-white">{editingJobId ? 'Update job' : 'Create a job'}</h2>
              <p className="mt-2 text-sm text-slate-400">Add roles here, then use the generated job ID in the ATS score panel.</p>
            </div>
            <div className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">
              {publishedCount} published
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-6">
          {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}
          {success ? <Alert className="border-emerald-400/40 bg-emerald-950/30 text-emerald-100">{success}</Alert> : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <Label htmlFor="job-title">Job title</Label>
              <Input id="job-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Frontend Engineer" />
            </div>
            <div>
              <Label htmlFor="job-locations">Locations</Label>
              <Input id="job-locations" value={locations} onChange={(event) => setLocations(event.target.value)} placeholder="Remote, New York" />
            </div>
          </div>

          <div>
            <Label htmlFor="job-description">Description</Label>
            <textarea
              id="job-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the role, responsibilities, and requirements."
              className="min-h-32 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none"
            />
          </div>

          <div>
            <Label htmlFor="job-skills">Required skills</Label>
            <Input id="job-skills" value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="React, Next.js, TypeScript" />
            <p className="mt-2 text-xs text-slate-500">Separate skills with commas.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <Label htmlFor="remote-type">Remote type</Label>
              <select
                id="remote-type"
                value={remoteType}
                onChange={(event) => setRemoteType(event.target.value as JobPayload['remote_type'])}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none"
              >
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
            <div>
              <Label htmlFor="job-status">Status</Label>
              <select
                id="job-status"
                value={status}
                onChange={(event) => setStatus(event.target.value as JobPayload['status'])}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none"
              >
                <option value="published">Published</option>
                <option value="draft">Draft</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <Label htmlFor="min-salary">Min salary</Label>
              <Input id="min-salary" value={minSalary} onChange={(event) => setMinSalary(event.target.value)} inputMode="numeric" placeholder="80000" />
            </div>
            <div>
              <Label htmlFor="max-salary">Max salary</Label>
              <Input id="max-salary" value={maxSalary} onChange={(event) => setMaxSalary(event.target.value)} inputMode="numeric" placeholder="120000" />
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="sm:w-40">
              <Label htmlFor="currency">Currency</Label>
              <Input id="currency" value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} placeholder="USD" />
            </div>
            {editingJobId ? (
              <Button type="button" variant="secondary" className="h-11 px-5" onClick={resetForm} disabled={isSubmitting}>
                <X className="mr-2 h-4 w-4" />
                Cancel edit
              </Button>
            ) : null}
            <Button type="submit" className="h-11 px-5" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
              {editingJobId ? 'Save job' : 'Create job'}
            </Button>
          </div>
        </form>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
        <div className="flex flex-col gap-3 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Jobs from backend</h2>
            <p className="mt-1 text-sm text-slate-400">These records come from `GET /api/v1/jobs`.</p>
          </div>
          <Button type="button" variant="secondary" onClick={loadJobs} disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Refresh
          </Button>
        </div>

        <div className="space-y-3 p-6">
          {!jobs.length && !isLoading ? (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center">
              <Briefcase className="mx-auto h-8 w-8 text-slate-500" />
              <p className="mt-3 text-sm text-slate-400">No jobs found. Create one above.</p>
            </div>
          ) : null}

          {jobs.map((job) => (
            <div key={job.id} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-white">{job.title}</h3>
                    <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-medium text-cyan-200">{job.status ?? 'draft'}</span>
                    {job.remote_type ? <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{job.remote_type}</span> : null}
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">{job.description || 'No description provided.'}</p>
                  <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                    <p>Skills: <span className="text-slate-300">{formatList(job.skills)}</span></p>
                    <p>Locations: <span className="text-slate-300">{formatList(job.locations)}</span></p>
                    <p>Job ID: <span className="font-mono text-slate-300">{job.id}</span></p>
                    <p>
                      Salary:{' '}
                      <span className="text-slate-300">
                        {job.min_salary || job.max_salary ? `${job.currency ?? ''} ${job.min_salary ?? '-'} - ${job.max_salary ?? '-'}` : 'Not set'}
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" size="sm" onClick={() => handleEdit(job)}>
                    <Edit3 className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button type="button" variant="secondary" size="sm" onClick={() => handleDelete(job.id)}>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
