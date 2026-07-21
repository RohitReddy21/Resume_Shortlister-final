"use client";

import { useEffect, useState } from "react";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  User,
  Video,
  MapPin,
  Search,
  Filter,
  Plus,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/dashboard-frame";
import { Button } from "@/components/ui/button";
import { listInterviews, rescheduleInterview, type Interview } from "@/lib/api";

type ViewMode = "month" | "week" | "day";

export default function InterviewCalendarPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<ViewMode>("month");

  const [search, setSearch] = useState("");
  const [interviewerFilter, setInterviewerFilter] = useState("All");
  const [selectedInterview, setSelectedInterview] = useState<Interview | null>(null);

  // Drag and drop state
  const [draggedInterviewId, setDraggedInterviewId] = useState<string | null>(null);

  useEffect(() => {
    fetchInterviews();
  }, []);

  async function fetchInterviews() {
    try {
      setLoading(true);
      const data = await listInterviews();
      setInterviews(data);
    } catch (err) {
      console.error("Failed to load calendar interviews:", err);
    } finally {
      setLoading(false);
    }
  }

  // Navigation handlers
  function handlePrev() {
    const next = new Date(currentDate);
    if (viewMode === "month") next.setMonth(next.getMonth() - 1);
    if (viewMode === "week") next.setDate(next.getDate() - 7);
    if (viewMode === "day") next.setDate(next.getDate() - 1);
    setCurrentDate(next);
  }

  function handleNext() {
    const next = new Date(currentDate);
    if (viewMode === "month") next.setMonth(next.getMonth() + 1);
    if (viewMode === "week") next.setDate(next.getDate() + 7);
    if (viewMode === "day") next.setDate(next.getDate() + 1);
    setCurrentDate(next);
  }

  function handleToday() {
    setCurrentDate(new Date());
  }

  // Drag & drop drop handler
  async function handleDropOnDate(targetDate: Date) {
    if (!draggedInterviewId) return;
    const interview = interviews.find((i) => i.id === draggedInterviewId);
    if (!interview) return;

    const currentScheduled = new Date(interview.scheduled_at);
    const newScheduled = new Date(targetDate);
    newScheduled.setHours(currentScheduled.getHours(), currentScheduled.getMinutes());

    try {
      await rescheduleInterview(interview.id, {
        scheduled_at: newScheduled.toISOString(),
      });
      fetchInterviews();
    } catch (err: any) {
      alert("Failed to reschedule via drag & drop: " + (err?.message || err));
    } finally {
      setDraggedInterviewId(null);
    }
  }

  // Filters
  const interviewersList = Array.from(
    new Set(interviews.map((i) => i.interviewer_name || i.interviewer).filter(Boolean))
  );

  const filteredInterviews = interviews.filter((i) => {
    const name = (i.candidate_name || "").toLowerCase();
    const title = (i.job_title || "").toLowerCase();
    const interviewer = (i.interviewer_name || i.interviewer || "").toLowerCase();
    const s = search.toLowerCase();
    const matchesSearch = !search || name.includes(s) || title.includes(s) || interviewer.includes(s);

    const matchesInterviewer =
      interviewerFilter === "All" || (i.interviewer_name || i.interviewer) === interviewerFilter;

    return matchesSearch && matchesInterviewer;
  });

  // Calendar Helpers for Month View
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const daysArray = [];
  for (let i = 0; i < firstDayOfMonth; i++) {
    daysArray.push(null);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    daysArray.push(new Date(year, month, d));
  }

  function getInterviewsForDate(date: Date | null) {
    if (!date) return [];
    const dateStr = date.toISOString().slice(0, 10);
    return filteredInterviews.filter((i) => {
      const scheduledStr = new Date(i.scheduled_at).toISOString().slice(0, 10);
      return scheduledStr === dateStr;
    });
  }

  // Week View Days
  const startOfWeek = new Date(currentDate);
  startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());
  const weekDays = Array.from({ length: 7 }).map((_, idx) => {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + idx);
    return d;
  });

  return (
    <DashboardFrame title="Interview Calendar" description="Visual schedule and drag-and-drop interview calendar">
      {/* Header controls */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        {/* Left: View selector & Navigation */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1 text-xs">
            {(["month", "week", "day"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                className={`rounded-lg px-3 py-1.5 capitalize font-medium transition-colors ${
                  viewMode === mode ? "bg-cyan-500/20 text-cyan-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {mode} View
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={handlePrev}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="secondary" size="sm" onClick={handleToday}>
              Today
            </Button>
            <Button variant="secondary" size="sm" onClick={handleNext}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="text-base font-semibold text-white">
            {currentDate.toLocaleString("default", { month: "long", year: "numeric" })}
          </div>
        </div>

        {/* Right: Search & Interviewer filter */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search calendar..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 w-full rounded-xl border border-slate-800 bg-slate-900/80 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-500/50"
            />
          </div>

          {interviewersList.length > 0 && (
            <select
              value={interviewerFilter}
              onChange={(e) => setInterviewerFilter(e.target.value)}
              className="h-9 rounded-xl border border-slate-800 bg-slate-900/80 px-3 text-xs text-slate-300 outline-none focus:border-cyan-500/50"
            >
              <option value="All">All Interviewers</option>
              {interviewersList.map((interviewer) => (
                <option key={interviewer as string} value={interviewer as string}>
                  {interviewer as string}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-800 border-t-cyan-400"></div>
        </div>
      ) : (
        <>
          {/* MONTH VIEW */}
          {viewMode === "month" && (
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-4">
              <div className="grid grid-cols-7 gap-2 mb-2 text-center text-xs font-semibold text-slate-400">
                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                  <div key={day} className="py-2">
                    {day}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-2">
                {daysArray.map((date, idx) => {
                  const dayInterviews = getInterviewsForDate(date);
                  const isToday =
                    date &&
                    new Date().toDateString() === date.toDateString();

                  return (
                    <div
                      key={idx}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={() => date && handleDropOnDate(date)}
                      className={`min-h-[110px] rounded-2xl border p-2 transition-all ${
                        date
                          ? isToday
                            ? "border-cyan-500/50 bg-cyan-500/5"
                            : "border-slate-800/80 bg-slate-900/30 hover:border-slate-700/80"
                          : "border-transparent bg-transparent"
                      }`}
                    >
                      {date && (
                        <>
                          <div className="flex items-center justify-between mb-1.5">
                            <span
                              className={`text-xs font-semibold ${
                                isToday
                                  ? "flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500 text-slate-950"
                                  : "text-slate-400"
                              }`}
                            >
                              {date.getDate()}
                            </span>
                            {dayInterviews.length > 0 && (
                              <span className="text-[10px] text-slate-500">
                                {dayInterviews.length} event{dayInterviews.length > 1 ? "s" : ""}
                              </span>
                            )}
                          </div>

                          <div className="space-y-1 overflow-y-auto max-h-[80px]">
                            {dayInterviews.map((interview) => (
                              <div
                                key={interview.id}
                                draggable
                                onDragStart={() => setDraggedInterviewId(interview.id)}
                                onClick={() => setSelectedInterview(interview)}
                                className="cursor-grab rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-1.5 text-xs text-cyan-300 transition-all hover:bg-cyan-500/20 active:cursor-grabbing"
                              >
                                <div className="truncate font-semibold">
                                  {interview.candidate_name || interview.candidate_id}
                                </div>
                                <div className="flex items-center gap-1 text-[10px] text-cyan-400/80">
                                  <Clock className="h-3 w-3" />
                                  {new Date(interview.scheduled_at).toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* WEEK VIEW */}
          {viewMode === "week" && (
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-4">
              <div className="grid grid-cols-7 gap-2">
                {weekDays.map((date) => {
                  const dayInterviews = getInterviewsForDate(date);
                  const isToday = new Date().toDateString() === date.toDateString();

                  return (
                    <div
                      key={date.toISOString()}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={() => handleDropOnDate(date)}
                      className={`min-h-[350px] rounded-2xl border p-3 ${
                        isToday ? "border-cyan-500/50 bg-cyan-500/5" : "border-slate-800/80 bg-slate-900/30"
                      }`}
                    >
                      <div className="text-center pb-2 border-b border-slate-800/80 mb-3">
                        <div className="text-xs uppercase text-slate-500 font-medium">
                          {date.toLocaleString("default", { weekday: "short" })}
                        </div>
                        <div className={`text-lg font-bold ${isToday ? "text-cyan-400" : "text-slate-200"}`}>
                          {date.getDate()}
                        </div>
                      </div>

                      <div className="space-y-2">
                        {dayInterviews.map((interview) => (
                          <div
                            key={interview.id}
                            draggable
                            onDragStart={() => setDraggedInterviewId(interview.id)}
                            onClick={() => setSelectedInterview(interview)}
                            className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900 p-2.5 hover:border-cyan-500/50 transition-all"
                          >
                            <div className="text-xs font-semibold text-white truncate">
                              {interview.candidate_name || interview.candidate_id}
                            </div>
                            <div className="text-[11px] text-slate-400 truncate mt-0.5">
                              {interview.interview_type || "Interview"}
                            </div>
                            <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                              <span>
                                {new Date(interview.scheduled_at).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </span>
                              <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-cyan-400">
                                {interview.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* DAY VIEW */}
          {viewMode === "day" && (
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-6">
              <div className="mb-4 text-base font-semibold text-white">
                {currentDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
              </div>

              {getInterviewsForDate(currentDate).length === 0 ? (
                <div className="py-12 text-center text-sm text-slate-500">
                  No interviews scheduled for this day.
                </div>
              ) : (
                <div className="space-y-3">
                  {getInterviewsForDate(currentDate).map((interview) => (
                    <div
                      key={interview.id}
                      onClick={() => setSelectedInterview(interview)}
                      className="cursor-pointer flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 hover:border-cyan-500/50 transition-all"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400">
                          <CalendarIcon className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-white">
                            {interview.candidate_name || interview.candidate_id}
                          </div>
                          <div className="text-xs text-slate-400">
                            {interview.job_title || "Job Application"} • {interview.interview_type}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-6 text-xs text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-4 w-4 text-slate-500" />
                          {new Date(interview.scheduled_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                        {interview.interviewer && (
                          <div className="flex items-center gap-1.5">
                            <User className="h-4 w-4 text-slate-500" />
                            {interview.interviewer_name || interview.interviewer}
                          </div>
                        )}
                        <span className="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-400 font-medium">
                          {interview.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Selected Interview Details Drawer / Modal */}
      {selectedInterview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-semibold text-white">
                {selectedInterview.interview_type || "Interview Details"}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedInterview(null)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Close
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              <div>
                <div className="text-slate-500 uppercase">Candidate</div>
                <div className="text-sm font-medium text-white">{selectedInterview.candidate_name || selectedInterview.candidate_id}</div>
              </div>
              <div>
                <div className="text-slate-500 uppercase">Job Title</div>
                <div className="text-sm font-medium text-white">{selectedInterview.job_title || selectedInterview.job_id}</div>
              </div>
              <div>
                <div className="text-slate-500 uppercase">Scheduled Time</div>
                <div>{new Date(selectedInterview.scheduled_at).toLocaleString()}</div>
              </div>
              {selectedInterview.interviewer && (
                <div>
                  <div className="text-slate-500 uppercase">Interviewer</div>
                  <div>{selectedInterview.interviewer_name || selectedInterview.interviewer}</div>
                </div>
              )}
              {selectedInterview.meeting_link && (
                <div>
                  <div className="text-slate-500 uppercase">Meeting Link</div>
                  <a
                    href={selectedInterview.meeting_link}
                    target="_blank"
                    rel="noreferrer"
                    className="text-cyan-400 hover:underline"
                  >
                    {selectedInterview.meeting_link}
                  </a>
                </div>
              )}
              {selectedInterview.notes && (
                <div>
                  <div className="text-slate-500 uppercase">Notes</div>
                  <div className="bg-slate-900 p-2 rounded-lg text-slate-400 mt-1">{selectedInterview.notes}</div>
                </div>
              )}
            </div>

            <div className="pt-2 text-right">
              <Button size="sm" onClick={() => setSelectedInterview(null)}>
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}
