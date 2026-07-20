"use client";

import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { CandidatePipelineTable } from '@/components/dashboard/candidate-pipeline-table';
import { ResumeUploadPanel } from '@/components/dashboard/resume-upload-panel';

export default function CandidatesPage() {
  return (
    <DashboardFrame
      title="Candidates"
      description="Review candidate profiles, current stage, and resume status from one queue."
    >
      <div className="space-y-6">
        <CandidatePipelineTable />
        <ResumeUploadPanel />
      </div>
    </DashboardFrame>
  );
}
