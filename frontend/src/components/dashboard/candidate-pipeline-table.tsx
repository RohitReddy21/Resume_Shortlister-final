"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Save, Trash2 } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  deleteApplication,
  isRejectedDeletionResult,
  listApplications,
  moveApplicationStage,
  updateApplication,
  updateCandidate,
  type ApplicationTableRow,
} from "@/lib/pipeline-api";
import { PIPELINE_STAGES, STAGE_CONFIG, type PipelineStage } from "@/types/pipeline";

interface CandidateDraft {
  first_name: string;
  last_name: string;
  email: string;
  headline: string;
  current_package: string;
  expected_package: string;
  notice_period: string;
  notes: string;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function formatMatch(score?: number | null) {
  return score === null || score === undefined ? "Not scored" : `${Math.round(score)}%`;
}

function statusClass(stage: PipelineStage) {
  const config = STAGE_CONFIG[stage] ?? STAGE_CONFIG.Applied;
  return `${config.color} ${config.textColor}`;
}

function draftFromRow(row: ApplicationTableRow): CandidateDraft {
  return {
    first_name: row.candidate.first_name ?? row.candidate.name?.split(" ")[0] ?? "",
    last_name: row.candidate.last_name ?? row.candidate.name?.split(" ").slice(1).join(" ") ?? "",
    email: row.candidate.raw_email ?? row.candidate.email ?? "",
    headline: row.candidate.headline ?? "",
    current_package: row.candidate.current_package ?? "",
    expected_package: row.candidate.expected_package ?? "",
    notice_period: row.candidate.notice_period ?? "",
    notes: row.notes ?? "",
  };
}

export function CandidatePipelineTable() {
  const [rows, setRows] = useState<ApplicationTableRow[]>([]);
  const [drafts, setDrafts] = useState<Record<string, CandidateDraft>>({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savingCandidateId, setSavingCandidateId] = useState<string | null>(null);
  const [savingNotesId, setSavingNotesId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const total = useMemo(() => rows.length, [rows]);

  async function loadRows() {
    setLoading(true);
    setError("");
    try {
      const data = await listApplications();
      setRows(data);
      setDrafts(
        Object.fromEntries(data.map((row) => [row.id, draftFromRow(row)])),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load candidate applications.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRows();
  }, []);

  async function handleStatusChange(row: ApplicationTableRow, stage: PipelineStage) {
    if (row.status === stage) return;

    setSavingId(row.id);
    setError("");
    setSuccess("");
    try {
      const result = await moveApplicationStage(row.id, stage, row.pipeline_order);
      if (isRejectedDeletionResult(result)) {
        setRows((current) =>
          result.deleted_scope === "candidate"
            ? current.filter((item) => item.candidate.id !== result.candidate_id)
            : current.filter((item) => item.id !== result.application_id),
        );
        setSuccess(result.message);
        return;
      }

      const updated = result;
      setRows((current) =>
        current.map((item) =>
          item.id === row.id
            ? {
                ...item,
                status: updated.status,
                pipeline_order: updated.pipeline_order,
                updated_at: updated.updated_at,
              }
            : item,
        ),
      );
      setSuccess(`${row.candidate.name || row.resume.title || "Candidate"} moved to ${stage}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update pipeline status.");
    } finally {
      setSavingId(null);
    }
  }

  function handleDraftChange(rowId: string, field: keyof CandidateDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [rowId]: {
        ...(current[rowId] ?? {
          first_name: "",
          last_name: "",
          email: "",
          headline: "",
          current_package: "",
          expected_package: "",
          notice_period: "",
          notes: "",
        }),
        [field]: value,
      },
    }));
  }

  async function handleCandidateSave(row: ApplicationTableRow) {
    const draft = drafts[row.id] ?? draftFromRow(row);
    setSavingCandidateId(row.candidate.id);
    setError("");
    setSuccess("");

    try {
      const updated = await updateCandidate(row.candidate.id, {
        first_name: draft.first_name,
        last_name: draft.last_name,
        email: draft.email,
        headline: draft.headline,
        current_package: draft.current_package,
        expected_package: draft.expected_package,
        notice_period: draft.notice_period,
      });
      setRows((current) =>
        current.map((item) =>
          item.candidate.id === row.candidate.id
            ? {
                ...item,
                candidate: {
                  ...item.candidate,
                  first_name: updated.first_name,
                  last_name: updated.last_name,
                  name: updated.name,
                  email: updated.email,
                  raw_email: updated.raw_email,
                  headline: updated.headline,
                  current_package: updated.current_package,
                  expected_package: updated.expected_package,
                  notice_period: updated.notice_period,
                },
              }
            : item,
        ),
      );
      setSuccess(`${updated.name || row.resume.title || "Candidate"} details saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save candidate details.");
    } finally {
      setSavingCandidateId(null);
    }
  }

  async function handleNotesSave(row: ApplicationTableRow) {
    const draft = drafts[row.id] ?? draftFromRow(row);
    setSavingNotesId(row.id);
    setError("");
    setSuccess("");

    try {
      const updated = await updateApplication(row.id, { notes: draft.notes });
      setRows((current) => current.map((item) => (item.id === row.id ? updated : item)));
      setDrafts((current) => ({ ...current, [row.id]: draftFromRow(updated) }));
      setSuccess("Application notes saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save application notes.");
    } finally {
      setSavingNotesId(null);
    }
  }

  async function handleDelete(row: ApplicationTableRow) {
    setDeletingId(row.id);
    setError("");
    setSuccess("");

    try {
      await deleteApplication(row.id);
      setRows((current) => current.filter((item) => item.id !== row.id));
      setSuccess(`${row.candidate.name || row.resume.title || "Application"} removed from pipeline.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete application.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
      <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Pipeline records</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Candidate status table</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">
            {total} application{total === 1 ? "" : "s"}
          </span>
          <Button type="button" variant="secondary" size="sm" onClick={loadRows} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Refresh
          </Button>
        </div>
      </div>

      <div className="space-y-4 p-6">
        {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}
        {success ? <Alert className="border-emerald-400/40 bg-emerald-950/30 text-emerald-100">{success}</Alert> : null}

        {loading ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
            Loading candidate applications
          </div>
        ) : null}

        {!loading && !rows.length ? (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 p-6 text-center text-sm text-slate-400">
            No pipeline applications found.
          </div>
        ) : null}

        {rows.length ? (
          <div className="overflow-x-auto rounded-2xl border border-slate-800">
            <table className="min-w-[1880px] w-full border-collapse text-left text-sm">
              <thead className="bg-slate-950 text-xs uppercase tracking-[0.22em] text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Candidate details</th>
                  <th className="px-4 py-3 font-medium">Job</th>
                  <th className="px-4 py-3 font-medium">Resume</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Current pkg</th>
                  <th className="px-4 py-3 font-medium">Expected pkg</th>
                  <th className="px-4 py-3 font-medium">Notice</th>
                  <th className="px-4 py-3 font-medium">Notes</th>
                  <th className="px-4 py-3 font-medium">ATS</th>
                  <th className="px-4 py-3 font-medium">Applied</th>
                  <th className="px-4 py-3 font-medium">Reason</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                {rows.map((row) => {
                  const draft = drafts[row.id] ?? draftFromRow(row);
                  const isSavingCandidate = savingCandidateId === row.candidate.id;
                  const isSavingNotes = savingNotesId === row.id;
                  const isDeleting = deletingId === row.id;

                  return (
                  <tr key={row.id} className="align-top transition hover:bg-slate-900/70">
                    <td className="px-4 py-4">
                      <div className="grid w-72 gap-2">
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            value={draft.first_name}
                            onChange={(event) => handleDraftChange(row.id, "first_name", event.target.value)}
                            placeholder="First name"
                            className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                          />
                          <input
                            value={draft.last_name}
                            onChange={(event) => handleDraftChange(row.id, "last_name", event.target.value)}
                            placeholder="Last name"
                            className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                          />
                        </div>
                        <input
                          value={draft.email}
                          onChange={(event) => handleDraftChange(row.id, "email", event.target.value)}
                          placeholder="Email"
                          className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                        />
                        <input
                          value={draft.headline}
                          onChange={(event) => handleDraftChange(row.id, "headline", event.target.value)}
                          placeholder="Current designation / headline"
                          className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                        />
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => handleCandidateSave(row)}
                          disabled={isSavingCandidate}
                          title="Save candidate details"
                        >
                          {isSavingCandidate ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                          Save candidate
                        </Button>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <p className="font-medium text-slate-200">{row.job.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{row.job.status || "No job status"}</p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-slate-300">{row.resume.title || "No resume"}</p>
                      <p className="mt-1 text-xs text-slate-500">{row.resume.status || "No resume status"}</p>
                    </td>
                    <td className="px-4 py-4">
                      <div className={`mb-2 inline-flex rounded-full border px-2.5 py-1 text-xs ${statusClass(row.status)}`}>
                        {STAGE_CONFIG[row.status]?.label ?? row.status}
                      </div>
                      <select
                        value={row.status}
                        onChange={(event) => handleStatusChange(row, event.target.value as PipelineStage)}
                        disabled={savingId === row.id}
                        className="block h-10 w-40 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition focus:border-cyan-400 disabled:text-slate-500"
                      >
                        {PIPELINE_STAGES.map((stage) => (
                          <option key={stage} value={stage}>
                            {STAGE_CONFIG[stage].label}
                          </option>
                        ))}
                      </select>
                      {savingId === row.id ? <p className="mt-2 text-xs text-cyan-300">Saving...</p> : null}
                    </td>
                    <td className="px-4 py-4">
                      <input
                        value={draft.current_package}
                        onChange={(event) => handleDraftChange(row.id, "current_package", event.target.value)}
                        placeholder="e.g. 6 LPA"
                        className="h-10 w-32 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                      />
                    </td>
                    <td className="px-4 py-4">
                      <input
                        value={draft.expected_package}
                        onChange={(event) => handleDraftChange(row.id, "expected_package", event.target.value)}
                        placeholder="e.g. 8 LPA"
                        className="h-10 w-32 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                      />
                    </td>
                    <td className="px-4 py-4">
                      <input
                        value={draft.notice_period}
                        onChange={(event) => handleDraftChange(row.id, "notice_period", event.target.value)}
                        placeholder="e.g. 30 days"
                        className="h-10 w-32 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                      />
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex w-64 items-start gap-2">
                        <textarea
                          value={draft.notes}
                          onChange={(event) => handleDraftChange(row.id, "notes", event.target.value)}
                          placeholder="Application notes"
                          rows={3}
                          className="min-h-20 flex-1 resize-none rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                        />
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => handleNotesSave(row)}
                          disabled={isSavingNotes}
                          title="Save application notes"
                        >
                          {isSavingNotes ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        </Button>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <p className="font-semibold text-cyan-300">{formatMatch(row.match_score)}</p>
                      {row.match_confidence !== null && row.match_confidence !== undefined ? (
                        <p className="mt-1 text-xs text-slate-500">{Math.round(row.match_confidence * 100)}% confidence</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-4 text-xs text-slate-400">{formatDate(row.applied_at)}</td>
                    <td className="px-4 py-4">
                      <p className="max-w-xs text-xs leading-5 text-slate-400">
                        {row.shortlist_reason || "No shortlist reason recorded"}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => handleDelete(row)}
                        disabled={isDeleting}
                        title="Delete application"
                      >
                        {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                        Delete
                      </Button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}
