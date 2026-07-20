"use client";

import { useEffect, useState } from 'react';
import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { KanbanBoard } from '@/components/kanban/kanban-board';
import { listJobs, type JobOption } from '@/lib/pipeline-api';
import { Briefcase, Loader2 } from 'lucide-react';

export default function PipelinePage() {
  const [jobs, setJobs] = useState<JobOption[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobOption | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listJobs()
      .then((data) => {
        setJobs(data);
        if (data.length > 0) {
          setSelectedJob(data[0]);
        }
      })
      .catch((err: any) => {
        setError(err.message || 'Failed to load jobs');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <DashboardFrame 
      title="Hiring Pipeline" 
      description="Monitor candidate movement from sourcing through offer."
      showRightPanel={false} // Board needs full width
    >
      <div className="space-y-6">
        {/* Job selector header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-cyan-950 border border-cyan-800 text-cyan-400">
              <Briefcase className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Select Job Position</h2>
              <p className="text-xs text-slate-400">View pipeline details for a specific opening</p>
            </div>
          </div>
          <div className="w-full sm:w-64">
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-slate-400 py-2">
                <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                <span>Loading positions...</span>
              </div>
            ) : error ? (
              <p className="text-xs text-rose-400">{error}</p>
            ) : jobs.length === 0 ? (
              <p className="text-sm text-slate-400">No active jobs found.</p>
            ) : (
              <select
                value={selectedJob?.id || ''}
                onChange={(e) => {
                  const job = jobs.find((j) => j.id === e.target.value);
                  if (job) setSelectedJob(job);
                }}
                className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition"
              >
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} ({job.status})
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Kanban Board */}
        {selectedJob ? (
          <KanbanBoard jobId={selectedJob.id} jobTitle={selectedJob.title} />
        ) : (
          !loading && (
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-3xl p-12 text-center">
              <Briefcase className="h-12 w-12 text-slate-600 mb-4" />
              <p className="text-sm text-slate-400">Create a job position first to see the candidate pipeline.</p>
            </div>
          )
        )}
      </div>
    </DashboardFrame>
  );
}

