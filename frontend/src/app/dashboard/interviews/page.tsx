"use client";

import { useEffect, useState } from "react";
import { Plus, Calendar, Clock, Video, MapPin, Edit, Trash2, XCircle, RotateCcw, CheckCircle2 } from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/dashboard-frame";
import { Button } from "@/components/ui/button";
import {
  listInterviews,
  createInterview,
  updateInterview,
  rescheduleInterview,
  cancelInterview,
  deleteInterview,
  type Interview,
} from "@/lib/api";

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/70 p-8 text-center text-slate-500">
      {label}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  let bg = "bg-slate-800";
  let text = "text-slate-300";
  if (status === "Scheduled") { bg = "bg-blue-500/20"; text = "text-blue-300"; }
  if (status === "Completed") { bg = "bg-green-500/20"; text = "text-green-300"; }
  if (status === "Cancelled") { bg = "bg-red-500/20"; text = "text-red-300"; }
  if (status === "No Show") { bg = "bg-orange-500/20"; text = "text-orange-300"; }
  if (status === "Rescheduled") { bg = "bg-purple-500/20"; text = "text-purple-300"; }
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${bg} ${text}`}>{status}</span>;
}

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingInterview, setEditingInterview] = useState<Interview | null>(null);
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
    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });

  useEffect(() => {
    fetchInterviews();
  }, []);

  async function fetchInterviews() {
    try {
      setLoading(true);
      const data = await listInterviews();
      setInterviews(data);
    } catch (err) {
      console.error("Failed to load interviews:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    try {
      if (editingInterview) {
        await updateInterview(editingInterview.id, form);
      } else {
        await createInterview(form as any);
      }
      setShowModal(false);
      setEditingInterview(null);
      setForm({
        interview_type: "HR Interview",
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      fetchInterviews();
    } catch (err) {
      console.error("Failed to save interview:", err);
    }
  }

  async function handleReschedule(interview: Interview) {
    setEditingInterview(interview);
    setForm({
      ...interview,
      scheduled_at: new Date(interview.scheduled_at).toISOString().slice(0, 16),
    });
    setShowModal(true);
  }

  async function handleConfirmReschedule() {
    if (!editingInterview) return;
    try {
      await rescheduleInterview(editingInterview.id, form);
      setShowModal(false);
      setEditingInterview(null);
      setForm({
        interview_type: "HR Interview",
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      fetchInterviews();
    } catch (err) {
      console.error("Failed to reschedule interview:", err);
    }
  }

  async function handleCancel(interview: Interview) {
    try {
      await cancelInterview(interview.id);
      fetchInterviews();
    } catch (err) {
      console.error("Failed to cancel interview:", err);
    }
  }

  async function handleDelete(interview: Interview) {
    if (!confirm("Are you sure you want to delete this interview?")) return;
    try {
      await deleteInterview(interview.id);
      fetchInterviews();
    } catch (err) {
      console.error("Failed to delete interview:", err);
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleString();
  }

  return (
    <DashboardFrame title="Interview Management" description="Schedule, manage, and track candidate interviews">
      <div className="mb-6 flex items-center justify-between">
        <div className="text-slate-400">Manage all interviews from one place</div>
        <Button type="button" onClick={() => setShowModal(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Schedule Interview
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-800 border-t-cyan-400"></div>
        </div>
      ) : interviews.length === 0 ? (
        <EmptyState label="No interviews yet. Click the button above to schedule your first interview!" />
      ) : (
        <div className="grid gap-4">
          {interviews.map((interview) => (
            <div key={interview.id} className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-6">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
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
                        onClick={() => {
                          setEditingInterview(interview);
                          setForm({
                            ...interview,
                            scheduled_at: new Date(interview.scheduled_at).toISOString().slice(0, 16),
                          });
                          setShowModal(true);
                        }}
                      >
                        <Edit className="mr-2 h-4 w-4" />
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleReschedule(interview)}
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Reschedule
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => handleCancel(interview)}
                      >
                        <XCircle className="mr-2 h-4 w-4" />
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
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Date & Time</div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <Calendar className="h-4 w-4 text-slate-500" />
                    {formatDate(interview.scheduled_at)}
                    {interview.time_zone && <span className="text-slate-500">({interview.time_zone})</span>}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Duration</div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <Clock className="h-4 w-4 text-slate-500" />
                    {interview.duration_minutes
                      ? `${interview.duration_minutes} min`
                      : interview.duration_minutes_str || "Not specified"}
                  </div>
                </div>
                {interview.meeting_link && (
                  <div className="space-y-1">
                    <div className="text-xs uppercase tracking-wider text-slate-500">Meeting Link</div>
                    <a
                      href={interview.meeting_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300"
                    >
                      <Video className="h-4 w-4" />
                      Join Meeting
                    </a>
                  </div>
                )}
                {interview.office_location && (
                  <div className="space-y-1">
                    <div className="text-xs uppercase tracking-wider text-slate-500">Location</div>
                    <div className="flex items-center gap-2 text-slate-300">
                      <MapPin className="h-4 w-4 text-slate-500" />
                      {interview.office_location}
                    </div>
                  </div>
                )}
              </div>

              {interview.interviewer && (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Interviewer</div>
                  <div className="text-slate-300">
                    {interview.interviewer_name || interview.interviewer}
                  </div>
                </div>
              )}

              {interview.notes && (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Notes</div>
                  <div className="text-slate-300 whitespace-pre-wrap">{interview.notes}</div>
                </div>
              )}

              {interview.rescheduled_from_id && (
                <div className="flex items-center gap-2 rounded-xl bg-purple-500/10 px-4 py-2 text-purple-300">
                  <RotateCcw className="h-4 w-4" />
                  Rescheduled from previous interview
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-3xl border border-slate-800 bg-slate-950 p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">
                {editingInterview
                  ? editingInterview.rescheduled_from_id
                    ? "Reschedule Interview"
                    : "Edit Interview"
                  : "Schedule Interview"}
              </h2>
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  setEditingInterview(null);
                  setForm({
                    interview_type: "HR Interview",
                    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                  });
                }}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="h-6 w-6" />
              </button>
            </div>

            <div className="grid gap-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Candidate ID</label>
                <input
                  type="text"
                  value={form.candidate_id || ""}
                  onChange={(e) => setForm({ ...form, candidate_id: e.target.value })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Job ID</label>
                <input
                  type="text"
                  value={form.job_id || ""}
                  onChange={(e) => setForm({ ...form, job_id: e.target.value })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Interview Type</label>
                <select
                  value={form.interview_type || "HR Interview"}
                  onChange={(e) => setForm({ ...form, interview_type: e.target.value })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  <option value="HR Interview">HR Interview</option>
                  <option value="Technical Interview">Technical Interview</option>
                  <option value="Manager Round">Manager Round</option>
                  <option value="Final Round">Final Round</option>
                  <option value="Client Round">Client Round</option>
                </select>
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Date & Time</label>
                <input
                  type="datetime-local"
                  value={form.scheduled_at || ""}
                  onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Duration (minutes)</label>
                <input
                  type="number"
                  value={form.duration_minutes || 30}
                  onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) || null })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Time Zone</label>
                <input
                  type="text"
                  value={form.time_zone || ""}
                  onChange={(e) => setForm({ ...form, time_zone: e.target.value })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Meeting Link</label>
                <input
                  type="url"
                  value={form.meeting_link || ""}
                  onChange={(e) => setForm({ ...form, meeting_link: e.target.value || null })}
                  placeholder="https://..."
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Office Location</label>
                <input
                  type="text"
                  value={form.office_location || ""}
                  onChange={(e) => setForm({ ...form, office_location: e.target.value || null })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Interviewer</label>
                <input
                  type="text"
                  value={form.interviewer || ""}
                  onChange={(e) => setForm({ ...form, interviewer: e.target.value || null })}
                  className="h-10 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-300">Notes</label>
                <textarea
                  value={form.notes || ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value || null })}
                  rows={4}
                  className="resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            <div className="mt-8 flex items-center justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowModal(false);
                  setEditingInterview(null);
                  setForm({
                    interview_type: "HR Interview",
                    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                  });
                }}
              >
                Cancel
              </Button>
              {editingInterview?.rescheduled_from_id ? (
                <Button type="button" onClick={handleConfirmReschedule}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Confirm Reschedule
                </Button>
              ) : (
                <Button type="button" onClick={handleSave}>
                  {editingInterview ? <Edit className="mr-2 h-4 w-4" /> : <Plus className="mr-2 h-4 w-4" />}
                  {editingInterview ? "Save Changes" : "Schedule Interview"}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}
