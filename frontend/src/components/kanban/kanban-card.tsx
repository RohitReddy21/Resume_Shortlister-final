"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { GripVertical, MessageSquare, Clock } from "lucide-react";
import type { ApplicationCard, PipelineStage } from "@/types/pipeline";
import { STAGE_CONFIG } from "@/types/pipeline";

interface KanbanCardProps {
  card: ApplicationCard;
  onDragStart: (card: ApplicationCard, sourceStage: PipelineStage) => void;
  onClick: (card: ApplicationCard) => void;
}

function isGeneratedCandidate(candidate: ApplicationCard["candidate"]): boolean {
  return (
    candidate.first_name === "Unknown" &&
    candidate.last_name === "Candidate" &&
    candidate.email.startsWith("unknown+") &&
    candidate.email.endsWith("@resumeparser.ai")
  );
}

function getCandidateName(candidate: ApplicationCard["candidate"]): string {
  if (isGeneratedCandidate(candidate)) {
    return "Name not detected";
  }
  return `${candidate.first_name} ${candidate.last_name}`.trim() || "Name not detected";
}

function getInitials(candidate: ApplicationCard["candidate"]): string {
  if (isGeneratedCandidate(candidate)) {
    return "ND";
  }
  return `${candidate.first_name.charAt(0)}${candidate.last_name.charAt(0)}`.toUpperCase() || "ND";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// Deterministic avatar color from candidate id
const AVATAR_COLORS = [
  "from-cyan-500 to-blue-600",
  "from-violet-500 to-purple-600",
  "from-amber-500 to-orange-600",
  "from-emerald-500 to-teal-600",
  "from-pink-500 to-rose-600",
];
function avatarColor(id: string): string {
  const idx = id.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

export function KanbanCard({ card, onDragStart, onClick }: KanbanCardProps) {
  const stage = card.status as PipelineStage;
  const cfg = STAGE_CONFIG[stage] ?? STAGE_CONFIG["Applied"];
  const candidateName = getCandidateName(card.candidate);
  const initials = getInitials(card.candidate);

  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", card.id);
      onDragStart(card, stage);
    },
    [card, stage, onDragStart]
  );

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onClick={() => onClick(card)}
      className="group relative cursor-pointer rounded-2xl border border-slate-700/60 bg-slate-900/90 p-4 shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-500 hover:shadow-lg hover:shadow-black/30 active:scale-[0.98] active:opacity-70"
    >
      {/* Drag handle */}
      <span className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-40">
        <GripVertical className="h-4 w-4 text-slate-400" />
      </span>

      {/* Candidate avatar + name */}
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-inner ${avatarColor(card.candidate.id)}`}
        >
          {initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">
            {candidateName}
          </p>
          {card.candidate.headline && (
            <p className="truncate text-xs text-slate-400">{card.candidate.headline}</p>
          )}
        </div>
      </div>

      {card.match_score !== null && card.match_score !== undefined ? (
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] uppercase tracking-[0.22em] text-slate-500">ATS match</span>
            <span className="text-sm font-semibold text-cyan-300">{Math.round(card.match_score)}%</span>
          </div>
          {card.shortlist_reason ? <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">{card.shortlist_reason}</p> : null}
        </div>
      ) : null}

      {/* Meta row */}
      <div className="mt-3 flex items-center justify-between gap-2">
        {/* Stage badge */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.color} ${cfg.textColor} bg-transparent`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>

        {/* Time + comments */}
        <div className="flex items-center gap-3">
          {card.comment_count > 0 && (
            <span className="flex items-center gap-1 text-[11px] text-slate-500">
              <MessageSquare className="h-3 w-3" />
              {card.comment_count}
            </span>
          )}
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <Clock className="h-3 w-3" />
            {timeAgo(card.applied_at)}
          </span>
        </div>
      </div>

      {/* Subtle source tag */}
      {card.source && (
        <span className="mt-2 block truncate text-[10px] text-slate-600 uppercase tracking-widest">
          via {card.source}
        </span>
      )}
    </div>
  );
}
