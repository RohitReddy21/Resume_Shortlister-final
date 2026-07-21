"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  Calendar,
  Clock,
  Video,
  MapPin,
  Edit,
  Trash2,
  XCircle,
  RotateCcw,
  Search,
  User,
  Briefcase,
  AlertCircle,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/dashboard-frame";
import { Button } from "@/components/ui/button";
import {
  listInterviews,
  createInterview,
  updateInterview,
  rescheduleInterview,
  cancelInterview,
  deleteInterview,
  listCandidates,
  listJobs,
  type Interview,
  type Candidate,
  type Job,
} from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  let bg = "bg-slate-800 border-slate-700 text-slate-300";
  if (status === "Scheduled") {
    bg = "bg-blue-500/10 border-blue-500/30 text-blue-400";
  }
  if (status === "Completed") {
    bg = "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
  }
  if (status === "Cancelled") {
    bg = "bg-rose-500/10 border-rose-500/30 text-rose-400";
  }
  if (status === "No Show") {
    bg = "bg-amber-500/10 border-amber-500/30 text-amber-400";
  }
  if (status === "Rescheduled") {
    bg = "bg-purple-500/10 border-purple-500/30 text-purple-400";
  }
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-0.5 text-xs font-medium ${bg}`}>
      {status}
    </span>
  );
}

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const [showModal, setShowModal] = useState(false);
  const [editingInterview, setEditingInterview] = useState<Interview | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const [form, setForm] = useState<Partial<{
    candidate_id: string;
    job_id: string;
    application_id?: string | null;
    interview_type?: string | null;
    scheduled_at: string;
    duration_minutes?: number | null;
    time_zone?: string | null;
    meeting_link?: string | null;
    office_location?: string | null;
    location?: string | null;
    mode?: string | null;
    interviewer?: string | null;
    notes?: string | null;
  }>>({
    interview_type: "HR Interview",
    duration_minutes: 30,
    time_zone: typeof window !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC",
  });

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      setLoading(true);
      setError(null);
      const [interviewsData, candidatesData, jobsData] = await Promise.all([
        listInterviews().catch(() => []),
        listCandidates().catch(() => []),
        listJobs().catch(() => []),
      ]);
      setInterviews(interviewsData);
      setCandidates(candidatesData);
      setJobs(jobsData);
    } catch (err: any) {
      console.error("Failed to load interviews:", err);
      setError(err?.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setForm({
      candidate_id: candidates[0]?.id || "",
      job_id: jobs[0]?.id || "",
      interview_type: "HR Interview",
      duration_minutes: 30,
      time_zone: typeof window !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC",
      scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    });
    setEditingInterview(null);
    setModalError(null);
  }

  function openCreateModal() {
    resetForm();
    setShowModal(true);
  }

  function openEditModal(interview: Interview) {
    setEditingInterview(interview);
    setForm({
      candidate_id: interview.candidate_id,
      job_id: interview.job_id,
      application_id: interview.application_id,
      interview_type: interview.interview_type || "HR Interview",
      scheduled_at: interview.scheduled_at ? new Date(interview.scheduled_at).toISOString().slice(0, 16) : "",
      duration_minutes: interview.duration_minutes || 30,
      time_zone: interview.time_zone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      meeting_link: interview.meeting_link || "",
      office_location: interview.office_location || "",
      interviewer: interview.interviewer || "",
      notes: interview.notes || "",
    });
    setModalError(null);
    setShowModal(true);
  }

  async function handleSave() {
    if (!form.candidate_id || !form.job_id || !form.scheduled_at) {
      setModalError("Candidate, Job, and Date/Time are required.");
      return;
    }
    try {
      setSubmitting(true);
      setModalError(null);
      const payload = {
        ...form,
        scheduled_at: new Date(form.scheduled_at!).toISOString(),
      };
      if (editingInterview) {
        if (editingInterview.rescheduled_from_id) {
          await rescheduleInterview(editingInterview.id, payload);
        } else {
          await updateInterview(editingInterview.id, payload);
        }
      } else {
        await createInterview(payload as any);
      }
      setShowModal(false);
      fetchData();
    } catch (err: any) {
      setModalError(err?.message || "Failed to save interview");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(interview: Interview) {
    try {
      await cancelInterview(interview.id);
      fetchData();
    } catch (err: any) {
      alert("Failed to cancel interview: " + (err?.message || err));
    }
  }

  async function handleDelete(interview: Interview) {
    if (!confirm("Are you sure you want to delete this interview?")) return;
    try {
      await deleteInterview(interview.id);
      fetchData();
    } catch (err: any) {
      alert("Failed to delete interview: " + (err?.message || err));
    }
  }

  const filteredInterviews = interviews.filter((interview) => {
    const matchesStatus = statusFilter === "All" || interview.status === statusFilter;
    const searchLower = searchTerm.toLowerCase();
    const candidateName = (interview.candidate_name || "").toLowerCase();
    const jobTitle = (interview.job_title || "").toLowerCase();
    const interviewer = (interview.interviewer || "").toLowerCase();
    const type = (interview.interview_type || "").toLowerCase();
    const matchesSearch =
      !searchTerm ||
      candidateName.includes(searchLower) ||
      jobTitle.includes(searchLower) ||
      interviewer.includes(searchLower) ||
      type.includes(searchLower);
    return matchesStatus && matchesSearch;
  });

  return (
    <DashboardFrame title="Interview Management" description="Schedule, manage, and track candidate interviews">
      {/* Action Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search candidate, job, interviewer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-10 w-full rounded-xl border border-slate-800 bg-slate-900/80 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1 text-xs">
            {["All", "Scheduled", "Completed", "Cancelled", "Rescheduled"].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                  statusFilter === st ? "bg-cyan-500/20 text-cyan-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <Button type="button" onClick={openCreateModal}>
          <Plus className="mr-2 h-4 w-4" />
          Schedule Interview
        </Button>
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
          <Button variant="secondary" size="sm" onClick={fetchData} className="ml-auto">
            Retry
          </Button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-6 w-32 rounded bg-slate-800"></div>
                <div className="h-6 w-20 rounded bg-slate-800"></div>
              </div>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="h-4 w-24 rounded bg-slate-800"></div>
                <div className="h-4 w-24 rounded bg-slate-800"></div>
                <div className="h-4 w-24 rounded bg-slate-800"></div>
                <div className="h-4 w-24 rounded bg-slate-800"></div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredInterviews.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-800 bg-slate-950/60 p-12 text-center">
          <Calendar className="mx-auto mb-3 h-10 w-10 text-slate-600" />
          <h3 className="text-base font-medium text-slate-300">No interviews found</h3>
          <p className="mt-1 text-sm text-slate-500">
            {searchTerm || statusFilter !== "All"
              ? "Try resetting your search or filter settings."
              : "Click the 'Schedule Interview' button above to get started."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredInterviews.map((interview) => (
            <div
              key={interview.id}
              className="flex flex-col gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 transition-all hover:border-slate-700/80"
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={interview.status} />
                  <div className="text-lg font-semibold text-white">
                    {interview.interview_type || "Interview"}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {interview.status === "Scheduled" && (
                    <>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => openEditModal(interview)}
                      >
                        <Edit className="mr-1.5 h-3.5 w-3.5" />
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => openEditModal({ ...interview, rescheduled_from_id: interview.id })}
                      >
                        <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                        Reschedule
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleCancel(interview)}
                      >
                        <XCircle className="mr-1.5 h-3.5 w-3.5" />
                        Cancel
                      </Button>
                    </>
                  )}
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => handleDelete(interview)}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5 text-rose-400" />
                    Delete
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Candidate</div>
                  <div className="flex items-center gap-2 text-sm text-slate-200">
                    <User className="h-4 w-4 text-cyan-400 shrink-0" />
                    <span className="font-medium">{interview.candidate_name || interview.candidate_id}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Job Title</div>
                  <div className="flex items-center gap-2 text-sm text-slate-200">
                    <Briefcase className="h-4 w-4 text-cyan-400 shrink-0" />
                    <span className="font-medium">{interview.job_title || interview.job_id}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Date & Time</div>
                  <div className="flex items-center gap-2 text-sm text-slate-200">
                    <Calendar className="h-4 w-4 text-slate-400 shrink-0" />
                    {new Date(interview.scheduled_at).toLocaleString()}
                    {interview.time_zone && <span className="text-slate-500">({interview.time_zone})</span>}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Duration</div>
                  <div className="flex items-center gap-2 text-sm text-slate-200">
                    <Clock className="h-4 w-4 text-slate-400 shrink-0" />
                    {interview.duration_minutes ? `${interview.duration_minutes} mins` : "30 mins"}
                  </div>
                </div>
              </div>

              {(interview.meeting_link || interview.office_location || interview.interviewer) && (
                <div className="flex flex-wrap items-center gap-6 border-t border-slate-800/60 pt-3 text-xs text-slate-400">
                  {interview.interviewer && (
                    <div>
                      <span className="text-slate-500">Interviewer: </span>
                      <span className="text-slate-200 font-medium">{interview.interviewer_name || interview.interviewer}</span>
                    </div>
                  )}
                  {interview.meeting_link && (
                    <a
                      href={interview.meeting_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 font-medium"
                    >
                      <Video className="h-3.5 w-3.5" />
                      Join Meeting Link
                    </a>
                  )}
                  {interview.office_location && (
                    <div className="flex items-center gap-1 text-slate-300">
                      <MapPin className="h-3.5 w-3.5 text-slate-500" />
                      {interview.office_location}
                    </div>
                  )}
                </div>
              )}

              {interview.notes && (
                <div className="text-xs text-slate-400 bg-slate-950/40 rounded-xl p-3 border border-slate-800/40">
                  <span className="text-slate-500 font-medium">Notes: </span>
                  {interview.notes}
                </div>
              )}

              {interview.rescheduled_from_id && (
                <div className="flex items-center gap-2 rounded-xl bg-purple-500/10 border border-purple-500/20 px-3 py-1.5 text-xs text-purple-300">
                  <RotateCcw className="h-3.5 w-3.5" />
                  Rescheduled from previous round
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal for Create/Edit/Reschedule */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl border border-slate-800 bg-slate-950 p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between mb-6 border-b border-slate-800/80 pb-4">
              <h2 className="text-lg font-semibold text-white">
                {editingInterview
                  ? editingInterview.rescheduled_from_id
                    ? "Reschedule Interview"
                    : "Edit Interview Details"
                  : "Schedule New Interview"}
              </h2>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="h-6 w-6" />
              </button>
            </div>

            {modalError && (
              <div className="mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-300">
                {modalError}
              </div>
            )}

            <div className="grid gap-4 text-sm">
              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Select Candidate *</label>
                {candidates.length > 0 ? (
                  <select
                    value={form.candidate_id || ""}
                    onChange={(e) => setForm({ ...form, candidate_id: e.target.value })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  >
                    <option value="">-- Choose Candidate --</option>
                    {candidates.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} ({c.email})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder="Candidate ID"
                    value={form.candidate_id || ""}
                    onChange={(e) => setForm({ ...form, candidate_id: e.target.value })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  />
                )}
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Select Job *</label>
                {jobs.length > 0 ? (
                  <select
                    value={form.job_id || ""}
                    onChange={(e) => setForm({ ...form, job_id: e.target.value })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  >
                    <option value="">-- Choose Job --</option>
                    {jobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder="Job ID"
                    value={form.job_id || ""}
                    onChange={(e) => setForm({ ...form, job_id: e.target.value })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  />
                )}
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Interview Type</label>
                <select
                  value={form.interview_type || "HR Interview"}
                  onChange={(e) => setForm({ ...form, interview_type: e.target.value })}
                  className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                >
                  <option value="HR Interview">HR Interview</option>
                  <option value="Technical Interview">Technical Interview</option>
                  <option value="Manager Round">Manager Round</option>
                  <option value="Final Round">Final Round</option>
                  <option value="Client Round">Client Round</option>
                </select>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <label className="font-medium text-slate-300">Date & Time *</label>
                  <input
                    type="datetime-local"
                    value={form.scheduled_at || ""}
                    onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="grid gap-2">
                  <label className="font-medium text-slate-300">Duration (Minutes)</label>
                  <input
                    type="number"
                    value={form.duration_minutes || 30}
                    onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) || 30 })}
                    className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Interviewer Name</label>
                <input
                  type="text"
                  placeholder="e.g. Jane Doe (Lead Engineer)"
                  value={form.interviewer || ""}
                  onChange={(e) => setForm({ ...form, interviewer: e.target.value })}
                  className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Meeting Link (Virtual)</label>
                <input
                  type="url"
                  placeholder="https://meet.google.com/..."
                  value={form.meeting_link || ""}
                  onChange={(e) => setForm({ ...form, meeting_link: e.target.value })}
                  className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Office Location (On-site)</label>
                <input
                  type="text"
                  placeholder="e.g. Conference Room A, HQ"
                  value={form.office_location || ""}
                  onChange={(e) => setForm({ ...form, office_location: e.target.value })}
                  className="h-10 rounded-xl border border-slate-800 bg-slate-900 px-3 text-white outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid gap-2">
                <label className="font-medium text-slate-300">Notes / Agenda</label>
                <textarea
                  placeholder="Add specific instructions, topics to cover..."
                  value={form.notes || ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={3}
                  className="resize-none rounded-xl border border-slate-800 bg-slate-900 p-3 text-white outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="mt-8 flex items-center justify-end gap-3 border-t border-slate-800/80 pt-4">
              <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button type="button" onClick={handleSave} disabled={submitting}>
                {submitting ? "Saving..." : editingInterview ? "Save Changes" : "Schedule Interview"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}
