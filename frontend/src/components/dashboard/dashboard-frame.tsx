"use client";

import Link from 'next/link';
import { ReactNode, useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { logout, me } from '@/lib/api';
import { clearTokens } from '@/lib/auth';
import { CalendarCard } from '@/components/dashboard/calendar-card';
import { DashboardShell } from '@/components/dashboard/dashboard-shell';
import { DashboardSidebar } from '@/components/dashboard/dashboard-sidebar';
import { NotificationCard } from '@/components/dashboard/notification-card';

interface DashboardFrameProps {
  children: ReactNode;
  eyebrow?: string;
  title: string;
  description?: string;
  showRightPanel?: boolean;
}

export function DashboardFrame({
  children,
  eyebrow = 'Recruiter workspace',
  title,
  description,
  showRightPanel = true,
}: DashboardFrameProps) {
  const router = useRouter();
  const [user, setUser] = useState<{ full_name?: string; role?: string } | null>(null);

  useEffect(() => {
    me()
      .then((payload) => setUser(payload))
      .catch(() => {
        clearTokens();
        router.push('/login');
      });
  }, [router]);

  async function handleLogout() {
    await logout();
    clearTokens();
    router.push('/login');
  }

  return (
    <DashboardShell
      sidebar={<DashboardSidebar />}
      header={
        <>
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-slate-400">{eyebrow}</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">{title}</h1>
            <p className="mt-2 text-sm text-slate-400">
              {description ?? (
                <>
                  Welcome back, <span className="font-semibold text-white">{user?.full_name ?? 'Recruiter'}</span>. Your role is{' '}
                  <span className="font-medium text-cyan-300">{user?.role ?? 'Recruiter'}</span>.
                </>
              )}
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <button className="rounded-full border border-slate-800 bg-slate-900/90 px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-400">
              Dark mode
            </button>
            <Link
              href="/dashboard/notifications"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
            >
              <Bell className="h-4 w-4" /> Notifications
            </Link>
            <button
              onClick={handleLogout}
              className="rounded-full border border-slate-800 bg-slate-900/90 px-4 py-2 text-sm text-slate-300 transition hover:border-rose-400"
            >
              Sign out
            </button>
          </div>
        </>
      }
      rightPanel={
        showRightPanel ? (
          <>
            <CalendarCard />
            <NotificationCard />
          </>
        ) : undefined
      }
    >
      {children}
    </DashboardShell>
  );
}
