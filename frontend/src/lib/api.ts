import { clearTokens, getAccessToken, getStoredTokens, saveTokens } from './auth';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NEXT_PUBLIC_API_HOSTNAME ? `https://${process.env.NEXT_PUBLIC_API_HOSTNAME}` : 'http://localhost:8000');

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const accessToken = getAccessToken();
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = errorText || 'Request failed';
    try {
      const errorBody = JSON.parse(errorText) as { detail?: string };
      errorMessage = errorBody.detail || errorMessage;
    } catch {
      // Keep the original response text when the server does not return JSON.
    }
    throw new Error(errorMessage);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }
  return response.text() as unknown as T;
}

async function downloadBlob(path: string, fallbackFileName: string, errorMessage: string) {
  const headers = new Headers();
  const accessToken = getAccessToken();
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error((await response.text()) || errorMessage);
  }

  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: await response.blob(),
    fileName: match?.[1] || fallbackFileName,
  };
}

export async function login(payload: { email: string; password: string }) {
  const response = await request<{ access_token: string; refresh_token: string }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  saveTokens(response);
  return response;
}

export async function signup(payload: { email: string; password: string; full_name: string; role?: string }) {
  const response = await request<{ access_token: string; refresh_token: string }>('/api/v1/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  saveTokens(response);
  return response;
}

export async function forgotPassword(email: string) {
  return request('/api/v1/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, newPassword: string) {
  return request('/api/v1/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function me() {
  const response = await request<{ id: string; email: string; full_name: string; role: string }>('/api/v1/auth/me');
  return response;
}

export async function logout() {
  const tokens = getStoredTokens();
  const response = await request('/api/v1/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: tokens?.refresh_token }),
  });
  clearTokens();
  return response;
}

export interface ATSScoreResponse {
  job_id: string;
  resume_id: string;
  total_score: number;
  score_percentage: number;
  weights: Record<string, number>;
  component_scores: Record<string, number>;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  explanation?: string | null;
}

export async function getATSScore(resumeId: string, jobId: string) {
  return request<ATSScoreResponse>(`/api/v1/ats/score/${encodeURIComponent(resumeId)}/${encodeURIComponent(jobId)}`);
}

export interface Job {
  id: string;
  title: string;
  description?: string | null;
  department_id?: string | null;
  hiring_manager_id?: string | null;
  skills?: string[] | null;
  locations?: string[] | null;
  remote_type?: 'onsite' | 'remote' | 'hybrid' | null;
  status?: 'draft' | 'published' | 'closed' | null;
  min_salary?: number | null;
  max_salary?: number | null;
  currency?: string | null;
}

export interface JobPayload {
  title: string;
  description?: string;
  skills?: string[];
  locations?: string[];
  remote_type?: 'onsite' | 'remote' | 'hybrid';
  status?: 'draft' | 'published' | 'closed';
  min_salary?: number;
  max_salary?: number;
  currency?: string;
}

export async function listJobs(status?: string) {
  const search = status ? `?status=${encodeURIComponent(status)}` : '';
  return request<Job[]>(`/api/v1/jobs${search}`);
}

export async function createJob(payload: JobPayload) {
  return request<Job>('/api/v1/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateJob(jobId: string, payload: Partial<JobPayload>) {
  return request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteJob(jobId: string) {
  return request<void>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
}

export interface ResumeUploadResponse {
  upload_id: string;
  resume_id: string;
  task_id?: string | null;
  file_name: string;
  saved_path: string;
  status: 'processing' | 'completed' | 'uploaded' | string;
  parse_mode?: 'celery' | 'inline' | 'not_parsed' | string;
  result?: unknown;
  warning?: string;
  error?: string;
}

export interface ResumeListItem {
  id: string;
  resume_id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_email?: string | null;
  title: string;
  source?: string | null;
  current_version_id?: string | null;
  status: 'parsed' | 'processing' | string;
  created_at?: string | null;
}

export interface ResumeStatusResponse {
  task_id: string;
  status: string;
  result?: {
    resume_id?: string;
    version_id?: string;
    status?: string;
  };
  error?: string;
}

export async function listResumes() {
  return request<ResumeListItem[]>('/api/v1/resumes');
}

export async function uploadResume(file: File, candidateId?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (candidateId?.trim()) {
    formData.append('candidate_id', candidateId.trim());
  }

  return request<ResumeUploadResponse>('/api/v1/resumes/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function getResumeStatus(taskId: string) {
  return request<ResumeStatusResponse>(`/api/v1/resumes/status/${encodeURIComponent(taskId)}`);
}

export async function getParsedResume(uploadId: string) {
  return request<Record<string, unknown>>(`/api/v1/resumes/parsed/${encodeURIComponent(uploadId)}`);
}

export async function parseResume(resumeId: string, force = false) {
  const search = force ? '?force=true' : '';
  return request<ResumeUploadResponse>(`/api/v1/resumes/${encodeURIComponent(resumeId)}/parse${search}`, {
    method: 'POST',
  });
}

export async function updateResume(resumeId: string, payload: { title?: string; source?: string | null }) {
  return request<ResumeListItem>(`/api/v1/resumes/${encodeURIComponent(resumeId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteResume(resumeId: string) {
  return request<void>(`/api/v1/resumes/${encodeURIComponent(resumeId)}`, {
    method: 'DELETE',
  });
}

export interface StructuredResumeExperience {
  company: string;
  title: string;
  start_date: string;
  end_date: string;
  location: string;
  description: string;
}

export interface StructuredResumeEducation {
  institution: string;
  degree: string;
  field: string;
  graduation_date: string;
  gpa: string;
}

export interface StructuredResumeData {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  summary: string;
  skills: string[];
  experience: StructuredResumeExperience[];
  education: StructuredResumeEducation[];
  certifications: string[];
}

export interface StructuredResumeRow {
  resume_id: string;
  candidate_id: string;
  resume_title: string;
  created_at?: string | null;
  structured: StructuredResumeData;
}

export async function listStructuredResumes() {
  return request<StructuredResumeRow[]>('/api/v1/resumes/structured');
}

export async function getStructuredResume(resumeId: string) {
  return request<StructuredResumeData>(`/api/v1/resumes/${encodeURIComponent(resumeId)}/structured`);
}

export async function updateStructuredResume(resumeId: string, payload: StructuredResumeData) {
  return request<StructuredResumeRow>(`/api/v1/resumes/${encodeURIComponent(resumeId)}/structured`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export interface ATSScreeningDashboard {
  total_candidates: number;
  shortlisted: number;
  rejected: number;
  average_experience: number;
  average_rating: number;
  top_10_candidates: Array<{
    candidate_name: string;
    rating: number;
    recommendation: string;
  }>;
  top_skills_found: string[];
  missing_skills_across_candidates: string[];
}

export interface ATSScreeningCandidate {
  resume_id: string;
  resume_title: string;
  rating: number;
  recommendation: string;
  reason: string;
  missing_skills: string[];
  interview_questions: string[];
  requirement_matches: Record<string, string>;
  report_row: Record<string, string | number>;
}

export interface ATSScreeningReport {
  job: {
    id: string;
    title: string;
    requirements: string[];
  };
  dashboard: ATSScreeningDashboard;
  candidates: ATSScreeningCandidate[];
}

export async function getATSScreeningReport(jobId: string) {
  return request<ATSScreeningReport>(`/api/v1/reports/ats-screening/${encodeURIComponent(jobId)}`);
}

export async function downloadATSScreeningReport(jobId: string) {
  return downloadBlob(
    `/api/v1/reports/ats-screening/${encodeURIComponent(jobId)}/excel`,
    'ats_screening_report.xlsx',
    'Unable to download ATS screening report.',
  );
}

export async function downloadResumeDataReport(jobId?: string) {
  const search = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  return downloadBlob(
    `/api/v1/reports/resume-data/excel${search}`,
    'resume_data_with_ats.xlsx',
    'Unable to download resume data report.',
  );
}

export async function downloadMaskedResume(resumeId: string) {
  return downloadBlob(
    `/api/v1/reports/masked-resumes/${encodeURIComponent(resumeId)}/pdf`,
    'masked_resume.pdf',
    'Unable to download masked resume.',
  );
}

export async function downloadMaskedResumesArchive() {
  return downloadBlob('/api/v1/reports/masked-resumes/zip', 'masked_resumes.zip', 'Unable to download masked resumes.');
}

export interface ApplicationCreatePayload {
  candidate_id: string;
  job_id: string;
  resume_id?: string;
  status?: 'Applied' | 'Screening' | 'Shortlisted' | 'Interview' | 'Technical' | 'HR' | 'Offer' | 'Hired' | 'Rejected';
  source?: string;
  notes?: string;
}

export interface ApplicationCreateResponse {
  id: string;
  status: string;
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
    first_name: string;
    last_name: string;
    email: string;
    headline?: string | null;
  };
  comment_count: number;
}

export async function createApplication(payload: ApplicationCreatePayload) {
  return request<ApplicationCreateResponse>('/api/v1/applications', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  link?: string | null;
  is_read: boolean;
  level: string;
  created_at: string;
}

export async function listNotifications() {
  return request<NotificationItem[]>('/api/v1/notifications');
}

export async function markNotificationRead(notificationId: string) {
  return request<NotificationItem>(`/api/v1/notifications/${encodeURIComponent(notificationId)}/read`, {
    method: 'PATCH',
  });
}

export async function deleteNotification(notificationId: string) {
  return request<void>(`/api/v1/notifications/${encodeURIComponent(notificationId)}`, {
    method: 'DELETE',
  });
}

export interface DashboardSummaryItem {
  title: string;
  subtitle: string;
  badge: string;
  meta: string;
}

export interface DashboardPipelineItem {
  stage: string;
  count: number;
  progress: number;
}

export interface DashboardSummary {
  stats: {
    candidates: number;
    open_jobs: number;
    applications: number;
    interviews: number;
    shortlisted: number;
  };
  pipeline: DashboardPipelineItem[];
  recent_candidates: DashboardSummaryItem[];
  recent_jobs: DashboardSummaryItem[];
}

export async function getDashboardSummary() {
  return request<DashboardSummary>('/api/v1/dashboard/summary');
}
