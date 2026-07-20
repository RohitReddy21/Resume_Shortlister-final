import { getAccessToken } from './auth';
import type {
  Activity,
  ApplicationCard,
  Comment,
  KanbanBoardData,
  MentionUser,
  PipelineStage,
} from '@/types/pipeline';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NEXT_PUBLIC_API_HOSTNAME ? `https://${process.env.NEXT_PUBLIC_API_HOSTNAME}` : 'http://localhost:8000');

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let msg = 'Request failed';
    try {
      const body = (await res.json()) as { detail?: string };
      msg = body.detail ?? msg;
    } catch {
      msg = await res.text().catch(() => msg);
    }
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') ?? '';
  return ct.includes('application/json')
    ? (res.json() as Promise<T>)
    : (res.text() as unknown as T);
}

// ── Board ──────────────────────────────────────────────────────────────────

export async function getKanbanBoard(jobId: string): Promise<KanbanBoardData> {
  return req<KanbanBoardData>(`/api/v1/pipeline/${encodeURIComponent(jobId)}`);
}

export interface ApplicationTableRow {
  id: string;
  status: PipelineStage;
  pipeline_order: number;
  match_score?: number | null;
  match_confidence?: number | null;
  shortlist_reason?: string | null;
  source?: string | null;
  notes?: string | null;
  applied_at: string;
  updated_at: string;
  candidate: {
    id: string;
    name?: string | null;
    email?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    raw_email?: string | null;
    phone?: string | null;
    headline?: string | null;
    current_package?: string | null;
    expected_package?: string | null;
    notice_period?: string | null;
  };
  job: {
    id: string;
    title: string;
    status?: string | null;
  };
  resume: {
    id?: string | null;
    title?: string | null;
    status?: string | null;
  };
  comment_count: number;
}

export async function listApplications(): Promise<ApplicationTableRow[]> {
  return req<ApplicationTableRow[]>('/api/v1/applications');
}

export interface CandidateUpdatePayload {
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  headline?: string | null;
  current_package?: string | null;
  expected_package?: string | null;
  notice_period?: string | null;
  summary?: string | null;
}

export async function updateCandidate(
  candidateId: string,
  payload: CandidateUpdatePayload,
): Promise<{
  id: string;
  first_name: string;
  last_name: string;
  name?: string | null;
  email?: string | null;
  raw_email: string;
  phone?: string | null;
  headline?: string | null;
  current_package?: string | null;
  expected_package?: string | null;
  notice_period?: string | null;
}> {
  return req(`/api/v1/candidates/${encodeURIComponent(candidateId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export interface CandidateCompensationPayload {
  current_package?: string | null;
  expected_package?: string | null;
  notice_period?: string | null;
}

export async function updateCandidateCompensation(
  candidateId: string,
  payload: CandidateCompensationPayload,
): Promise<{ id: string; current_package?: string | null; expected_package?: string | null; notice_period?: string | null }> {
  return req(`/api/v1/candidates/${encodeURIComponent(candidateId)}/compensation`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function updateApplication(
  appId: string,
  payload: Partial<Pick<ApplicationTableRow, 'status' | 'pipeline_order' | 'source' | 'notes'>>,
): Promise<ApplicationTableRow> {
  return req<ApplicationTableRow>(`/api/v1/applications/${encodeURIComponent(appId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteApplication(appId: string): Promise<void> {
  return req<void>(`/api/v1/applications/${encodeURIComponent(appId)}`, {
    method: 'DELETE',
  });
}

// ── Stage move ─────────────────────────────────────────────────────────────

export interface RejectedDeletionResult {
  deleted: true;
  deleted_scope: 'candidate' | 'application';
  application_id: string;
  candidate_id: string;
  resume_ids?: string[];
  message: string;
}

export type StageMoveResult = ApplicationCard | RejectedDeletionResult;

export function isRejectedDeletionResult(result: StageMoveResult): result is RejectedDeletionResult {
  return (result as RejectedDeletionResult).deleted === true;
}

export async function moveApplicationStage(
  appId: string,
  stage: PipelineStage,
  pipelineOrder?: number,
): Promise<StageMoveResult> {
  return req<StageMoveResult>(`/api/v1/applications/${encodeURIComponent(appId)}/stage`, {
    method: 'PATCH',
    body: JSON.stringify({ stage, pipeline_order: pipelineOrder }),
  });
}

// ── Activity ───────────────────────────────────────────────────────────────

export async function getActivity(appId: string): Promise<Activity[]> {
  return req<Activity[]>(`/api/v1/applications/${encodeURIComponent(appId)}/activity`);
}

// ── Comments ───────────────────────────────────────────────────────────────

export async function getComments(appId: string): Promise<Comment[]> {
  return req<Comment[]>(`/api/v1/applications/${encodeURIComponent(appId)}/comments`);
}

export async function addComment(
  appId: string,
  body: string,
  mentions: string[],
): Promise<Comment> {
  return req<Comment>(`/api/v1/applications/${encodeURIComponent(appId)}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body, mentions }),
  });
}

export async function updateComment(
  appId: string,
  commentId: string,
  body: string,
  mentions: string[],
): Promise<Comment> {
  return req<Comment>(`/api/v1/applications/${encodeURIComponent(appId)}/comments/${encodeURIComponent(commentId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ body, mentions }),
  });
}

export async function deleteComment(appId: string, commentId: string): Promise<void> {
  return req<void>(`/api/v1/applications/${encodeURIComponent(appId)}/comments/${encodeURIComponent(commentId)}`, {
    method: 'DELETE',
  });
}

// ── Mention autocomplete ───────────────────────────────────────────────────

export async function searchMentionUsers(q: string): Promise<MentionUser[]> {
  return req<MentionUser[]>(`/api/v1/pipeline/users/search?q=${encodeURIComponent(q)}`);
}

// ── Jobs list (for job selector) ───────────────────────────────────────────

export interface JobOption {
  id: string;
  title: string;
  status: string;
}

export async function listJobs(): Promise<JobOption[]> {
  return req<JobOption[]>(`/api/v1/jobs`);
}
