"use client";

import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { ATSScreeningReportPanel } from '@/components/dashboard/ats-screening-report-panel';
import { JobManager } from '@/components/dashboard/job-manager';

export default function JobsPage() {
  return (
    <DashboardFrame title="Jobs" description="Manage job openings, priority roles, and candidate flow by position.">
      <div className="space-y-6">
        <ATSScreeningReportPanel />
        <JobManager />
      </div>
    </DashboardFrame>
  );
}
