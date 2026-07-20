// Pipeline types for the Kanban recruitment board

export const PIPELINE_STAGES = [
  "Applied",
  "Screening",
  "Shortlisted",
  "Interview",
  "Technical",
  "HR",
  "Offer",
  "Hired",
  "Rejected",
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export interface CandidateSnippet {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  headline?: string | null;
}

export interface ApplicationCard {
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
  candidate: CandidateSnippet;
  comment_count: number;
}

export interface KanbanBoardData {
  job_id: string;
  job_title: string;
  columns: Record<PipelineStage, ApplicationCard[]>;
}

export interface Comment {
  id: string;
  application_id: string;
  author_id: string;
  author_name: string;
  body: string;
  mentions: string[];
  created_at: string;
}

export interface Activity {
  id: string;
  action: string;
  details?: string | null;
  author_name?: string | null;
  created_at: string;
}

export interface MentionUser {
  id: string;
  full_name: string;
  email: string;
}

// Stage display config
export const STAGE_CONFIG: Record<
  PipelineStage,
  { label: string; color: string; bgGradient: string; dot: string; textColor: string }
> = {
  Applied:     { label: "Applied",     color: "border-slate-500",   bgGradient: "from-slate-800 to-slate-900",     dot: "bg-slate-400",    textColor: "text-slate-300" },
  Screening:   { label: "Screening",   color: "border-blue-500",    bgGradient: "from-blue-900/60 to-slate-900",   dot: "bg-blue-400",     textColor: "text-blue-300"  },
  Shortlisted: { label: "Shortlisted", color: "border-violet-500",  bgGradient: "from-violet-900/60 to-slate-900", dot: "bg-violet-400",   textColor: "text-violet-300"},
  Interview:   { label: "Interview",   color: "border-amber-500",   bgGradient: "from-amber-900/60 to-slate-900",  dot: "bg-amber-400",    textColor: "text-amber-300" },
  Technical:   { label: "Technical",   color: "border-orange-500",  bgGradient: "from-orange-900/60 to-slate-900", dot: "bg-orange-400",   textColor: "text-orange-300"},
  HR:          { label: "HR Round",    color: "border-pink-500",    bgGradient: "from-pink-900/60 to-slate-900",   dot: "bg-pink-400",     textColor: "text-pink-300"  },
  Offer:       { label: "Offer",       color: "border-cyan-500",    bgGradient: "from-cyan-900/60 to-slate-900",   dot: "bg-cyan-400",     textColor: "text-cyan-300"  },
  Hired:       { label: "Hired ✓",    color: "border-emerald-500", bgGradient: "from-emerald-900/60 to-slate-900",dot: "bg-emerald-400",  textColor: "text-emerald-300"},
  Rejected:    { label: "Rejected",    color: "border-rose-500",    bgGradient: "from-rose-900/60 to-slate-900",   dot: "bg-rose-400",     textColor: "text-rose-300"  },
};
