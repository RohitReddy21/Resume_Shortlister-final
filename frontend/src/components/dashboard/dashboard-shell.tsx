"use client";

import { ReactNode, useState } from 'react';
import { Menu, X } from 'lucide-react';

interface DashboardShellProps {
  sidebar: ReactNode;
  header: ReactNode;
  children: ReactNode;
  rightPanel?: ReactNode;
}

export function DashboardShell({ sidebar, header, children, rightPanel }: DashboardShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="sticky top-0 z-40 flex items-center justify-between border-b border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur lg:hidden">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-400">ResumeParser.AI</p>
          <p className="mt-1 text-sm font-semibold text-white">Recruiter dashboard</p>
        </div>
        <button
          type="button"
          onClick={() => setIsMobileNavOpen(true)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-slate-200"
          aria-label="Open navigation menu"
          aria-expanded={isMobileNavOpen}
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {isMobileNavOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/70"
            onClick={() => setIsMobileNavOpen(false)}
            aria-label="Close navigation menu"
          />
          <aside className="relative flex h-full w-[min(88vw,340px)] flex-col overflow-y-auto border-r border-slate-800 bg-slate-900 p-5 shadow-2xl">
            <div className="mb-5 flex items-center justify-between gap-4">
              <p className="text-sm font-semibold text-white">Navigation</p>
              <button
                type="button"
                onClick={() => setIsMobileNavOpen(false)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 text-slate-300"
                aria-label="Close navigation menu"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {sidebar}
          </aside>
        </div>
      ) : null}

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside className="hidden w-[320px] flex-col border-r border-slate-800 bg-slate-900/95 p-6 lg:flex">
          {sidebar}
        </aside>
        <main className="flex-1 px-4 py-6 lg:px-8">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">{header}</div>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <section className="space-y-6">{children}</section>
            {rightPanel ? <aside className="space-y-6">{rightPanel}</aside> : null}
          </div>
        </main>
      </div>
    </div>
  );
}
