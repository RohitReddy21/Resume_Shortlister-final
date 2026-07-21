"use client";

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { getCandidate, type Candidate } from '@/lib/api';
import { Loader2 } from 'lucide-react';

export default function CandidateDetailPage() {
  const { candidateId } = useParams();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!candidateId || typeof candidateId !== 'string') return;
    getCandidate(candidateId)
      .then(setCandidate)
      .finally(() => setLoading(false));
  }, [candidateId]);

  if (loading) {
    return (
      <DashboardFrame title="Candidate Profile">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
        </div>
      </DashboardFrame>
    );
  }

  if (!candidate) {
    return (
      <DashboardFrame title="Candidate Profile">
        <div className="text-center py-12 text-slate-400">Candidate not found</div>
      </DashboardFrame>
    );
  }

  return (
    <DashboardFrame title={`${candidate.name || `${candidate.first_name} ${candidate.last_name}`}`}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Personal Information */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 border border-slate-800 rounded-2xl bg-slate-950">
            <h3 className="text-lg font-semibold text-white mb-4">Personal Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Full Name</label>
                <p className="text-slate-300 mt-1">{candidate.first_name} {candidate.last_name}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Email</label>
                <p className="text-slate-300 mt-1">{candidate.email || candidate.raw_email}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Phone</label>
                <p className="text-slate-300 mt-1">{candidate.phone || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Address</label>
                <p className="text-slate-300 mt-1">{candidate.address || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">LinkedIn</label>
                {candidate.linkedin ? (
                  <a href={candidate.linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 mt-1">
                    {candidate.linkedin}
                  </a>
                ) : (
                  <p className="text-slate-300 mt-1">-</p>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">GitHub</label>
                {candidate.github ? (
                  <a href={candidate.github} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 mt-1">
                    {candidate.github}
                  </a>
                ) : (
                  <p className="text-slate-300 mt-1">-</p>
                )}
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Portfolio</label>
                {candidate.portfolio ? (
                  <a href={candidate.portfolio} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 mt-1">
                    {candidate.portfolio}
                  </a>
                ) : (
                  <p className="text-slate-300 mt-1">-</p>
                )}
              </div>
            </div>
          </div>

          {/* Professional Information */}
          <div className="p-6 border border-slate-800 rounded-2xl bg-slate-950">
            <h3 className="text-lg font-semibold text-white mb-4">Professional Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Current Company</label>
                <p className="text-slate-300 mt-1">{candidate.current_company || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Current Designation</label>
                <p className="text-slate-300 mt-1">{candidate.current_designation || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Experience</label>
                <p className="text-slate-300 mt-1">{candidate.total_experience || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Relevant Experience</label>
                <p className="text-slate-300 mt-1">{candidate.relevant_experience || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Current Salary</label>
                <p className="text-slate-300 mt-1">{candidate.current_package || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Expected Salary</label>
                <p className="text-slate-300 mt-1">{candidate.expected_package || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Notice Period</label>
                <p className="text-slate-300 mt-1">{candidate.notice_period || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Preferred Location</label>
                <p className="text-slate-300 mt-1">{candidate.preferred_location || '-'}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Employment Type</label>
                <p className="text-slate-300 mt-1">{candidate.employment_type || '-'}</p>
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Summary</label>
                <p className="text-slate-300 mt-1 whitespace-pre-wrap">{candidate.summary || '-'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar (Resumes & Stats) */}
        <div className="space-y-6">
          <div className="p-6 border border-slate-800 rounded-2xl bg-slate-950">
            <h3 className="text-lg font-semibold text-white mb-4">Overview</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Resumes</span>
                <span className="text-slate-300 font-medium">{candidate.resume_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Applications</span>
                <span className="text-slate-300 font-medium">{candidate.application_count}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardFrame>
  );
}
