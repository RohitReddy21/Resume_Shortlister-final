"use client";

import { ChangeEvent, useEffect, useMemo, useState } from 'react';
import { Briefcase, FileText, Loader2, RefreshCw, Search, Upload } from 'lucide-react';
import {
  createApplication,
  getParsedResume,
  getResumeStatus,
  listJobs,
  listResumes,
  parseResume,
  uploadResume,
  type Job,
  type ResumeListItem,
  type ResumeStatusResponse,
  type ResumeUploadResponse,
} from '@/lib/api';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface UploadedResumeState extends ResumeUploadResponse {
  statusResult?: ResumeStatusResponse;
  parsedPreview?: Record<string, unknown>;
}

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (['completed', 'success', 'parsed'].includes(normalized)) return 'bg-emerald-400/10 text-emerald-200 border-emerald-400/30';
  if (['failed', 'failure', 'not_parsed'].includes(normalized)) return 'bg-rose-400/10 text-rose-200 border-rose-400/30';
  return 'bg-amber-400/10 text-amber-200 border-amber-400/30';
}

function getParsedName(parsed?: Record<string, unknown>) {
  const fullName = parsed?.full_name;
  if (fullName && typeof fullName === 'object' && 'value' in fullName) {
    return String((fullName as { value?: unknown }).value ?? '');
  }
  return '';
}

function getParsedListCount(parsed: Record<string, unknown> | undefined, key: string) {
  const value = parsed?.[key];
  return Array.isArray(value) ? value.length : 0;
}

export function ResumeUploadPanel() {
  const [candidateId, setCandidateId] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploads, setUploads] = useState<UploadedResumeState[]>([]);
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState('');
  const [applicationResumeId, setApplicationResumeId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingResumes, setIsLoadingResumes] = useState(false);
  const [parsingResumeId, setParsingResumeId] = useState<string | null>(null);

  const parsedCount = useMemo(() => resumes.filter((resume) => resume.status === 'parsed').length, [resumes]);
  const selectedJob = useMemo(() => jobs.find((job) => job.id === selectedJobId) ?? null, [jobs, selectedJobId]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
    setError('');
    setSuccess('');
  }

  async function loadResumes() {
    setIsLoadingResumes(true);
    setError('');
    try {
      const payload = await listResumes();
      setResumes(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load resumes.');
    } finally {
      setIsLoadingResumes(false);
    }
  }

  async function loadJobs() {
    try {
      const payload = await listJobs();
      setJobs(payload);
      setSelectedJobId((current) => current || payload[0]?.id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load jobs.');
    }
  }

  useEffect(() => {
    loadResumes();
    loadJobs();
  }, []);

  async function handleUpload() {
    if (!files.length) {
      setError('Choose one or more resume files first.');
      return;
    }

    setIsUploading(true);
    setError('');
    setSuccess('');

    const uploaded: UploadedResumeState[] = [];
    try {
      for (const file of files) {
        const response = await uploadResume(file, candidateId);
        uploaded.push(response);
      }
      setUploads((current) => [...uploaded, ...current]);
      setFiles([]);
      setSuccess(`Uploaded ${uploaded.length} resume${uploaded.length === 1 ? '' : 's'}.`);
      await loadResumes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to upload resume.');
      if (uploaded.length) {
        setUploads((current) => [...uploaded, ...current]);
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function checkStatus(upload: UploadedResumeState) {
    if (!upload.task_id) {
      try {
        const parsed = await getParsedResume(upload.upload_id);
        setUploads((current) =>
          current.map((item) => (item.upload_id === upload.upload_id ? { ...item, parsedPreview: parsed, status: String(parsed.status ?? item.status) } : item)),
        );
        await loadResumes();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load parsed resume.');
      }
      return;
    }

    try {
      const status = await getResumeStatus(upload.task_id);
      let parsedPreview: Record<string, unknown> | undefined;
      if (status.result?.resume_id || status.status.toLowerCase() === 'success') {
        try {
          parsedPreview = await getParsedResume(upload.upload_id);
        } catch {
          parsedPreview = undefined;
        }
      }

      setUploads((current) =>
        current.map((item) =>
          item.upload_id === upload.upload_id
            ? {
                ...item,
                status: status.result?.status ?? status.status,
                statusResult: status,
                parsedPreview,
              }
            : item,
        ),
      );
      await loadResumes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to check parse status.');
    }
  }

  async function handleCreateApplication(resume: ResumeListItem) {
    if (!selectedJobId) {
      setError('Select or create a job before adding a resume to the pipeline.');
      return;
    }
    if (resume.status !== 'parsed') {
      setError('Parse this resume before scoring and shortlisting it.');
      return;
    }

    setApplicationResumeId(resume.resume_id);
    setError('');
    setSuccess('');

    try {
      const created = await createApplication({
        candidate_id: resume.candidate_id,
        job_id: selectedJobId,
        resume_id: resume.resume_id,
        source: 'resume_upload',
      });
      const score = created.match_score !== null && created.match_score !== undefined ? ` (${Math.round(created.match_score)}% match)` : '';
      setSuccess(`${resume.candidate_name || resume.title} was scored and moved to ${created.status}${score}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to add candidate to the pipeline.';
      if (message.toLowerCase().includes('already has an application')) {
        setSuccess(`${resume.candidate_name || resume.title} is already in ${selectedJob?.title || 'the selected job'} pipeline.`);
      } else {
        setError(message);
      }
    } finally {
      setApplicationResumeId(null);
    }
  }

  async function handleParseResume(resume: ResumeListItem, force = false) {
    setParsingResumeId(resume.resume_id);
    setError('');
    setSuccess('');

    try {
      const parsed = await parseResume(resume.resume_id, force);
      setUploads((current) => [parsed, ...current.filter((item) => item.resume_id !== resume.resume_id)]);
      setSuccess(`${resume.title} was ${force ? 're-parsed' : 'parsed'} and is ready for scoring.`);
      await loadResumes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to parse resume.');
    } finally {
      setParsingResumeId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
        <div className="border-b border-slate-800 px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Resume intake</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Upload candidate resumes</h2>
              <p className="mt-2 text-sm text-slate-400">
                Upload one or more resumes. If parsing completes, use the resume ID in ATS scoring.
              </p>
            </div>
            <div className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">
              {parsedCount} parsed
            </div>
          </div>
        </div>

        <div className="space-y-5 p-6">
          {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}
          {success ? <Alert className="border-emerald-400/40 bg-emerald-950/30 text-emerald-100">{success}</Alert> : null}

          <div className="grid gap-4 lg:grid-cols-[minmax(0,0.45fr)_minmax(0,0.55fr)]">
            <div>
              <Label htmlFor="candidate-id">Existing candidate ID optional</Label>
              <Input
                id="candidate-id"
                value={candidateId}
                onChange={(event) => setCandidateId(event.target.value)}
                placeholder="Leave empty to let parser detect candidate"
              />
            </div>
            <div>
              <Label htmlFor="resume-files">Resume files</Label>
              <input
                id="resume-files"
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="block w-full cursor-pointer rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-300 file:mr-4 file:rounded-full file:border-0 file:bg-cyan-500 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-950 hover:file:bg-cyan-400"
              />
            </div>
          </div>

          {files.length ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-sm font-semibold text-white">Ready to upload</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {files.map((file) => (
                  <span key={`${file.name}-${file.size}`} className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
                    {file.name}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-5 text-slate-500">
              Without Redis/Celery, the backend attempts inline parsing so local uploads still produce a resume record.
            </p>
            <Button type="button" onClick={handleUpload} disabled={isUploading}>
              {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              Upload resumes
            </Button>
          </div>
        </div>
      </div>

      {uploads.length ? (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
          <div className="border-b border-slate-800 px-6 py-5">
            <h2 className="text-xl font-semibold text-white">Recent uploads</h2>
            <p className="mt-1 text-sm text-slate-400">Check parse status and copy resume IDs for ATS scoring.</p>
          </div>
          <div className="space-y-3 p-6">
            {uploads.map((upload) => (
              <div key={upload.upload_id} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <FileText className="h-4 w-4 text-cyan-300" />
                      <h3 className="truncate text-base font-semibold text-white">{upload.file_name}</h3>
                      <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusTone(upload.status)}`}>{upload.status}</span>
                      {upload.parse_mode ? <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{upload.parse_mode}</span> : null}
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                      <p>Resume ID: <span className="font-mono text-slate-300">{upload.resume_id}</span></p>
                      <p>Task ID: <span className="font-mono text-slate-300">{upload.task_id ?? 'No async task'}</span></p>
                    </div>
                    {upload.warning ? <p className="mt-3 text-sm text-amber-200">{upload.warning}</p> : null}
                    {upload.error ? <p className="mt-3 text-sm text-rose-200">{upload.error}</p> : null}
                    {upload.parsedPreview ? (
                      <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-sm text-slate-300">
                        <p>Name: <span className="text-white">{getParsedName(upload.parsedPreview) || 'Not detected'}</span></p>
                        <p className="mt-1">
                          Extracted {getParsedListCount(upload.parsedPreview, 'skills')} skills, {getParsedListCount(upload.parsedPreview, 'experiences')} experience entries, and{' '}
                          {getParsedListCount(upload.parsedPreview, 'education')} education entries.
                        </p>
                      </div>
                    ) : null}
                  </div>
                  <Button type="button" variant="secondary" size="sm" onClick={() => checkStatus(upload)}>
                    <Search className="mr-2 h-4 w-4" />
                    Check status
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
        <div className="flex flex-col gap-3 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Uploaded resumes</h2>
            <p className="mt-1 text-sm text-slate-400">Select a job, then let the backend score and shortlist parsed resumes.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <select
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
              disabled={!jobs.length}
              className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none disabled:text-slate-500"
            >
              {jobs.length ? (
                jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} ({job.status ?? 'draft'})
                  </option>
                ))
              ) : (
                <option value="">No jobs found</option>
              )}
            </select>
            <Button type="button" variant="secondary" onClick={loadResumes} disabled={isLoadingResumes}>
              {isLoadingResumes ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              Refresh
            </Button>
          </div>
        </div>

        <div className="space-y-3 p-6">
          {!resumes.length && !isLoadingResumes ? (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center">
              <FileText className="mx-auto h-8 w-8 text-slate-500" />
              <p className="mt-3 text-sm text-slate-400">No uploaded resumes found.</p>
            </div>
          ) : null}

          {resumes.map((resume) => {
            const isParsed = resume.status === 'parsed';
            const isParsing = parsingResumeId === resume.resume_id;
            const isScoring = applicationResumeId === resume.resume_id;

            return (
            <div key={resume.id} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate text-base font-semibold text-white">{resume.title}</h3>
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusTone(resume.status)}`}>{resume.status}</span>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-slate-500 lg:grid-cols-2">
                    <p>Resume ID: <span className="font-mono text-slate-300">{resume.resume_id}</span></p>
                    <p>Candidate ID: <span className="font-mono text-slate-300">{resume.candidate_id}</span></p>
                    <p>Candidate: <span className="text-slate-300">{resume.candidate_name || 'Name not detected'}</span></p>
                    <p>Email: <span className="text-slate-300">{resume.candidate_email || 'Email not detected'}</span></p>
                  </div>
                </div>
                <div className="flex flex-col items-start gap-3 md:items-end">
                  <p className="text-xs text-slate-500">{resume.created_at ? new Date(resume.created_at).toLocaleString() : ''}</p>
                  {isParsed ? (
                    <div className="flex flex-wrap items-center justify-start gap-2 md:justify-end">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleParseResume(resume, true)}
                        disabled={isParsing}
                      >
                        {isParsing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                        Re-parse
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleCreateApplication(resume)}
                        disabled={!selectedJobId || isScoring}
                      >
                        {isScoring ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Briefcase className="mr-2 h-4 w-4" />}
                        Score and shortlist
                      </Button>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => handleParseResume(resume)}
                      disabled={isParsing}
                    >
                      {isParsing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                      Parse resume
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
          })}
        </div>
      </div>
    </div>
  );
}
