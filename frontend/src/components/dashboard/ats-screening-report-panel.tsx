"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, Loader2, RefreshCw } from "lucide-react";
import {
  downloadATSScreeningReport,
  getATSScreeningReport,
  listJobs,
  type ATSScreeningReport,
  type Job,
} from "@/lib/api";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

function formatList(values: string[]) {
  return values.length ? values.join(", ") : "Not Found";
}

export function ATSScreeningReportPanel() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [report, setReport] = useState<ATSScreeningReport | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedJob = useMemo(() => jobs.find((job) => job.id === selectedJobId), [jobs, selectedJobId]);

  async function loadJobs() {
    setLoadingJobs(true);
    setError("");
    try {
      const data = await listJobs();
      setJobs(data);
      setSelectedJobId((current) => current || data.find((job) => job.status === "published")?.id || data[0]?.id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load jobs.");
    } finally {
      setLoadingJobs(false);
    }
  }

  async function loadReport(jobId = selectedJobId) {
    if (!jobId) return;
    setLoadingReport(true);
    setError("");
    setSuccess("");
    try {
      const data = await getATSScreeningReport(jobId);
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate ATS screening report.");
    } finally {
      setLoadingReport(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      loadReport(selectedJobId);
    }
  }, [selectedJobId]);

  async function handleDownload() {
    if (!selectedJobId) return;
    setDownloading(true);
    setError("");
    setSuccess("");
    try {
      const { blob, fileName } = await downloadATSScreeningReport(selectedJobId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setSuccess("Excel report downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download Excel report.");
    } finally {
      setDownloading(false);
    }
  }

  const dashboard = report?.dashboard;

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90">
      <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">ATS report</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Resume screening Excel</h2>
          <p className="mt-2 text-sm text-slate-400">Compare every parsed resume against the selected job description.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <select
            value={selectedJobId}
            onChange={(event) => setSelectedJobId(event.target.value)}
            disabled={loadingJobs}
            className="h-10 min-w-72 rounded-full border border-slate-700 bg-slate-950 px-4 text-sm text-white outline-none transition focus:border-cyan-400"
          >
            {!jobs.length ? <option value="">No jobs found</option> : null}
            {jobs.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
          <Button type="button" variant="secondary" size="sm" onClick={() => loadReport()} disabled={!selectedJobId || loadingReport}>
            {loadingReport ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Refresh
          </Button>
          <Button type="button" size="sm" onClick={handleDownload} disabled={!selectedJobId || downloading || loadingReport}>
            {downloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            Download Excel
          </Button>
        </div>
      </div>

      <div className="space-y-5 p-6">
        {error ? <Alert className="border-rose-400/40 bg-rose-950/30 text-rose-100">{error}</Alert> : null}
        {success ? <Alert className="border-emerald-400/40 bg-emerald-950/30 text-emerald-100">{success}</Alert> : null}

        {selectedJob ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-sm font-semibold text-white">{selectedJob.title}</p>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">{selectedJob.description || "No job description provided."}</p>
            <p className="mt-2 text-xs text-slate-500">Required skills: <span className="text-slate-300">{formatList(selectedJob.skills ?? [])}</span></p>
          </div>
        ) : null}

        {loadingReport ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
            Generating screening report
          </div>
        ) : null}

        {dashboard ? (
          <>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {[
                ["Total Candidates", dashboard.total_candidates],
                ["Shortlisted", dashboard.shortlisted],
                ["Rejected", dashboard.rejected],
                ["Avg Experience", `${dashboard.average_experience}`],
                ["Avg Rating", `${dashboard.average_rating}/10`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 xl:col-span-2">
                <h3 className="text-sm font-semibold text-white">Top candidates</h3>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[560px] text-left text-sm">
                    <thead className="text-xs uppercase tracking-[0.2em] text-slate-500">
                      <tr>
                        <th className="pb-3 font-medium">Candidate</th>
                        <th className="pb-3 font-medium">Rating</th>
                        <th className="pb-3 font-medium">Recommendation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {dashboard.top_10_candidates.map((candidate) => (
                        <tr key={`${candidate.candidate_name}-${candidate.rating}`}>
                          <td className="py-3 text-white">{candidate.candidate_name}</td>
                          <td className="py-3 text-cyan-200">{candidate.rating}/10</td>
                          <td className="py-3 text-slate-300">{candidate.recommendation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <h3 className="text-sm font-semibold text-white">Top skills found</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{formatList(dashboard.top_skills_found)}</p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <h3 className="text-sm font-semibold text-white">Missing skills across candidates</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{formatList(dashboard.missing_skills_across_candidates)}</p>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
