"use client";

import { useCallback, useState } from "react";
import { Plus } from "lucide-react";
import type { ApplicationCard, PipelineStage } from "@/types/pipeline";
import { STAGE_CONFIG } from "@/types/pipeline";
import { KanbanCard } from "./kanban-card";

interface KanbanColumnProps {
  stage: PipelineStage;
  cards: ApplicationCard[];
  onDragStart: (card: ApplicationCard, sourceStage: PipelineStage) => void;
  onDrop: (targetStage: PipelineStage, targetIndex: number) => void;
  onCardClick: (card: ApplicationCard) => void;
}

export function KanbanColumn({
  stage,
  cards,
  onDragStart,
  onDrop,
  onCardClick,
}: KanbanColumnProps) {
  const cfg = STAGE_CONFIG[stage];
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    // Only clear if leaving the column entirely (not entering a child)
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      onDrop(stage, cards.length);
    },
    [stage, cards.length, onDrop]
  );

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex w-72 flex-shrink-0 flex-col rounded-3xl border transition-all duration-200 ${
        isDragOver
          ? `${cfg.color} bg-gradient-to-b ${cfg.bgGradient} shadow-lg shadow-black/20`
          : "border-slate-800 bg-slate-900/60"
      }`}
    >
      {/* Column header */}
      <div
        className={`flex items-center justify-between rounded-t-3xl bg-gradient-to-r ${cfg.bgGradient} px-4 py-3`}
      >
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
          <span className={`text-sm font-semibold ${cfg.textColor}`}>{cfg.label}</span>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${cfg.textColor} border ${cfg.color} bg-slate-950/40`}
        >
          {cards.length}
        </span>
      </div>

      {/* Cards list */}
      <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {cards.length === 0 && (
          <div
            className={`flex h-20 items-center justify-center rounded-2xl border-2 border-dashed transition-colors ${
              isDragOver ? `${cfg.color} opacity-60` : "border-slate-700/40 opacity-40"
            }`}
          >
            <p className="text-xs text-slate-500">Drop here</p>
          </div>
        )}
        {cards.map((card) => (
          <KanbanCard
            key={card.id}
            card={card}
            onDragStart={onDragStart}
            onClick={onCardClick}
          />
        ))}

        {/* Drop zone at end of column when cards exist */}
        {isDragOver && cards.length > 0 && (
          <div
            className={`h-1.5 rounded-full ${cfg.dot} opacity-60 animate-pulse`}
          />
        )}
      </div>
    </div>
  );
}
