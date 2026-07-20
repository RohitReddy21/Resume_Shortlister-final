"use client";

import { Bell } from 'lucide-react';
import { DashboardFrame } from '@/components/dashboard/dashboard-frame';
import { NotificationCard } from '@/components/dashboard/notification-card';

export default function NotificationsPage() {
  return (
    <DashboardFrame
      title="Notifications"
      description="Review candidate activity, interview updates, and team reminders."
      showRightPanel={false}
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.6fr)_minmax(0,0.4fr)]">
        <NotificationCard />
        <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
          <Bell className="h-5 w-5 text-cyan-300" />
          <h2 className="mt-4 text-lg font-semibold text-white">Notification settings</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Keep important hiring events visible on mobile and desktop without relying on the right-side dashboard panel.
          </p>
        </div>
      </div>
    </DashboardFrame>
  );
}
