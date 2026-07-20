"use client";

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Loader2, Trash2 } from 'lucide-react';
import { deleteNotification, listNotifications, markNotificationRead, type NotificationItem } from '@/lib/api';

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.max(0, Math.floor(diff / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function NotificationCard() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [markingId, setMarkingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const unreadCount = useMemo(() => notifications.filter((item) => !item.is_read).length, [notifications]);

  async function loadNotifications() {
    setLoading(true);
    setError('');
    try {
      setNotifications(await listNotifications());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load notifications.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotifications();
  }, []);

  async function handleMarkRead(id: string) {
    setMarkingId(id);
    setError('');
    try {
      const updated = await markNotificationRead(id);
      setNotifications((current) => current.map((item) => (item.id === id ? updated : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update notification.');
    } finally {
      setMarkingId(null);
    }
  }

  async function handleMarkAllRead() {
    const unread = notifications.filter((item) => !item.is_read);
    if (!unread.length) return;

    setMarkingId('all');
    setError('');
    try {
      const updated = await Promise.all(unread.map((item) => markNotificationRead(item.id)));
      setNotifications((current) =>
        current.map((item) => updated.find((next) => next.id === item.id) ?? item),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update notifications.');
    } finally {
      setMarkingId(null);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    setError('');
    try {
      await deleteNotification(id);
      setNotifications((current) => current.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete notification.');
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Notifications</p>
          <h3 className="mt-2 text-lg font-semibold text-white">Activity feed</h3>
        </div>
        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={!unreadCount || markingId === 'all'}
          className="text-sm text-cyan-300 transition hover:text-cyan-200 disabled:cursor-not-allowed disabled:text-slate-600"
        >
          {markingId === 'all' ? 'Updating...' : `Mark read${unreadCount ? ` (${unreadCount})` : ''}`}
        </button>
      </div>

      <div className="mt-6 space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 rounded-3xl border border-slate-800 bg-slate-950/95 p-4 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
            Loading notifications
          </div>
        ) : null}

        {error ? (
          <div className="rounded-3xl border border-rose-400/30 bg-rose-950/30 p-4 text-sm text-rose-100">{error}</div>
        ) : null}

        {!loading && !error && notifications.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/70 p-4 text-sm text-slate-500">
            No notifications yet.
          </div>
        ) : null}

        {notifications.map((item) => {
          const content = (
            <>
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-white">{item.title}</p>
                <span className="shrink-0 text-xs uppercase tracking-[0.28em] text-slate-500">{timeAgo(item.created_at)}</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{item.message}</p>
            </>
          );

          return (
            <div
              key={item.id}
              className={`rounded-3xl border p-4 ${
                item.is_read
                  ? 'border-slate-800 bg-slate-950/70'
                  : 'border-cyan-400/30 bg-cyan-950/20'
              }`}
            >
              {item.link ? (
                <Link href={item.link} className="block">
                  {content}
                </Link>
              ) : (
                content
              )}
              <div className="mt-3 flex items-center gap-3">
                {!item.is_read ? (
                  <button
                    type="button"
                    onClick={() => handleMarkRead(item.id)}
                    disabled={markingId === item.id}
                    className="text-xs font-medium text-cyan-300 transition hover:text-cyan-200 disabled:text-slate-600"
                  >
                    {markingId === item.id ? 'Updating...' : 'Mark as read'}
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  disabled={deletingId === item.id}
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 transition hover:text-rose-300 disabled:text-slate-700"
                >
                  {deletingId === item.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
