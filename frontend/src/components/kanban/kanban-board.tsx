"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, ChevronRight, Loader2, RefreshCw } from "lucide-react";
import type { ApplicationCard, KanbanBoardData, PipelineStage } from "@/types/pipeline";
import { PIPELINE_STAGES } from "@/types/pipeline";
import { getKanbanBoard, isRejectedDeletionResult, moveApplicationStage } from "@/lib/pipeline-api";
import { KanbanColumn } from "./kanban-column";
import { CandidateDrawer } from "./candidate-drawer";

interface KanbanBoardProps {
  jobId: string;
  jobTitle: string;
}

export function KanbanBoard({ jobId, jobTitle }: KanbanBoardProps) {
  const [board, setBoard] = useState<KanbanBoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<ApplicationCard | null>(null);
  const [moving, setMoving] = useState<string | null>(null); // appId being moved

  // Drag state
  const draggingCard = useRef<ApplicationCard | null>(null);
  const draggingSourceStage = useRef<PipelineStage | null>(null);

  const loadBoard = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getKanbanBoard(jobId);
      setBoard(data);
    } catch (err: any) {
      setError(err?.message ?? "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const handleDragStart = useCallback((card: ApplicationCard, sourceStage: PipelineStage) => {
    draggingCard.current = card;
    draggingSourceStage.current = sourceStage;
  }, []);

  const handleDrop = useCallback(
    async (targetStage: PipelineStage, targetIndex: number) => {
      const card = draggingCard.current;
      const sourceStage = draggingSourceStage.current;
      draggingCard.current = null;
      draggingSourceStage.current = null;

      if (!card || !board || !sourceStage || sourceStage === targetStage) return;

      // Optimistic update
      setBoard((prev) => {
        if (!prev) return prev;
        const cols = { ...prev.columns };
        cols[sourceStage] = cols[sourceStage].filter((c) => c.id !== card.id);
        const moved = { ...card, status: targetStage };
        cols[targetStage] = [...cols[targetStage], moved];
        return { ...prev, columns: cols };
      });

      setMoving(card.id);
      try {
        const result = await moveApplicationStage(card.id, targetStage, targetIndex);
        if (isRejectedDeletionResult(result)) {
          setBoard((prev) => {
            if (!prev) return prev;
            const columns = { ...prev.columns };
            for (const stage of PIPELINE_STAGES) {
              columns[stage] = columns[stage].filter((item) =>
                result.deleted_scope === "candidate"
                  ? item.candidate.id !== result.candidate_id
                  : item.id !== result.application_id,
              );
            }
            return { ...prev, columns };
          });
          setSelectedCard((current) => {
            if (!current) return current;
            return result.deleted_scope === "candidate"
              ? current.candidate.id === result.candidate_id
                ? null
                : current
              : current.id === result.application_id
                ? null
                : current;
          });
        }
      } catch (err) {
        console.error("Stage move failed, reverting", err);
        // Revert on error
        loadBoard();
      } finally {
        setMoving(null);
      }
    },
    [board, loadBoard]
  );

  const totalCards = board
    ? Object.values(board.columns).reduce((sum, col) => sum + col.length, 0)
    : 0;

  // ── Loading skeleton ──
  if (loading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4 pt-2">
        {PIPELINE_STAGES.map((stage) => (
          <div
            key={stage}
            className="flex w-72 flex-shrink-0 animate-pulse flex-col rounded-3xl border border-slate-800 bg-slate-900/60"
          >
            <div className="h-12 rounded-t-3xl bg-slate-800/60" />
            <div className="space-y-3 p-3">
              {[1, 2].map((n) => (
                <div key={n} className="h-24 rounded-2xl bg-slate-800/40" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // ── Error state ──
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <AlertCircle className="h-10 w-10 text-rose-400" />
        <p className="text-sm text-slate-400">{error}</p>
        <button
          onClick={loadBoard}
          className="inline-flex items-center gap-2 rounded-full bg-slate-800 px-4 py-2 text-sm text-white transition hover:bg-slate-700"
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      </div>
    );
  }

  if (!board) return null;

  return (
    <>
      {/* Board meta bar */}
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <ChevronRight className="h-4 w-4 text-cyan-400" />
          <span className="font-medium text-white">{jobTitle}</span>
          <span>·</span>
          <span>{totalCards} candidate{totalCards !== 1 ? "s" : ""}</span>
        </div>
        <button
          onClick={loadBoard}
          className="inline-flex items-center gap-2 rounded-full border border-slate-800 px-3 py-1.5 text-xs text-slate-400 transition hover:border-slate-600 hover:text-white"
        >
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
      </div>

      {/* Move indicator */}
      {moving && (
        <div className="mb-3 flex items-center gap-2 rounded-2xl border border-cyan-800/50 bg-cyan-900/20 px-4 py-2 text-sm text-cyan-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          Saving stage change…
        </div>
      )}

      {/* Scrollable Kanban board */}
      <div className="flex gap-4 overflow-x-auto pb-6 pt-1 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700">
        {PIPELINE_STAGES.map((stage) => (
          <KanbanColumn
            key={stage}
            stage={stage}
            cards={board.columns[stage] ?? []}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
            onCardClick={setSelectedCard}
          />
        ))}
      </div>

      {/* Candidate detail drawer */}
      <CandidateDrawer card={selectedCard} jobId={jobId} onClose={() => setSelectedCard(null)} />
    </>
  );
}
