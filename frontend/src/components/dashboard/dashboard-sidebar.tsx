"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, Briefcase, Calendar, FileText, FolderOpen, Sparkles, UserPlus } from 'lucide-react';

const navItems = [
  { label: 'Overview', icon: Sparkles, href: '/dashboard' },
  { label: 'Candidates', icon: UserPlus, href: '/dashboard/candidates' },
  { label: 'Resume data', icon: FileText, href: '/dashboard/resume-data' },
  { label: 'Jobs', icon: Briefcase, href: '/dashboard/jobs' },
  { label: 'Pipeline', icon: FolderOpen, href: '/dashboard/pipeline' },
  { label: 'Interviews', icon: Calendar, href: '/dashboard/interviews' },
  { label: 'Notifications', icon: Bell, href: '/dashboard/notifications' },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col justify-between">
      <div className="space-y-10">
        <div>
          <Link href="/dashboard" className="text-sm uppercase tracking-[0.35em] text-cyan-400">
            ResumeParser.AI
          </Link>
          <h2 className="mt-4 text-2xl font-semibold text-white">Recruiter dashboard</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">Manage candidates, jobs, and the hiring pipeline in one place.</p>
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = item.href === '/dashboard' ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link
                key={item.label}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={`flex w-full items-center gap-3 rounded-3xl px-4 py-3 text-left text-sm transition ${
                  isActive ? 'bg-slate-800 text-white shadow-sm shadow-cyan-500/10' : 'text-slate-400 hover:bg-slate-950 hover:text-white'
                }`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900/95 p-5">
        <p className="text-sm text-slate-400">Pro recruiter features</p>
        <div className="mt-4 space-y-2 rounded-3xl bg-slate-950/80 p-4">
          <p className="text-sm font-semibold text-white">Team collaboration</p>
          <p className="text-sm text-slate-400">Streamline hiring from lead to offer.</p>
        </div>
      </div>
    </div>
  );
}
