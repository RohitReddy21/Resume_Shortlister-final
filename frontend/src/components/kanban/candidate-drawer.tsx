"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  Edit3,
  MessageSquare,
  Send,
  Trash2,
  User,
  X,
  Clock,
  GitPullRequestArrow,
  FileText,
} from "lucide-react";
import type { Activity, ApplicationCard, Comment, MentionUser } from "@/types/pipeline";
import { STAGE_CONFIG } from "@/types/pipeline";
import { addComment, deleteComment, getActivity, getComments, searchMentionUsers, updateComment } from "@/lib/pipeline-api";
import { sendResumeChat } from "@/lib/api";

interface CandidateDrawerProps {
  card: ApplicationCard | null;
  jobId?: string | null;
  onClose: () => void;
}

type Tab = "activity" | "comments" | "ai-chat";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
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

function getCandidateEmail(candidate: ApplicationCard["candidate"]): string {
  if (candidate.email.startsWith("unknown+") && candidate.email.endsWith("@resumeparser.ai")) {
    return "Email not detected";
  }
  return candidate.email;
}

function getInitials(candidate: ApplicationCard["candidate"]) {
  if (isGeneratedCandidate(candidate)) {
    return "ND";
  }
  return `${candidate.first_name.charAt(0)}${candidate.last_name.charAt(0)}`.toUpperCase() || "ND";
}

function actionIcon(action: string) {
  if (action === "stage_change") return <ArrowRight className="h-3.5 w-3.5" />;
  if (action === "comment") return <MessageSquare className="h-3.5 w-3.5" />;
  if (action === "upload") return <FileText className="h-3.5 w-3.5" />;
  return <GitPullRequestArrow className="h-3.5 w-3.5" />;
}

export function CandidateDrawer({ card, jobId, onClose }: CandidateDrawerProps) {
  const [tab, setTab] = useState<Tab>("activity");
  const [activity, setActivity] = useState<Activity[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentBody, setCommentBody] = useState("");
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionUsers, setMentionUsers] = useState<MentionUser[]>([]);
  const [mentionedIds, setMentionedIds] = useState<string[]>([]);
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentBusyId, setCommentBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load data when card changes
  useEffect(() => {
    if (!card) return;
    setLoading(true);
    setActivity([]);
    setComments([]);
    Promise.all([getActivity(card.id), getComments(card.id)])
      .then(([acts, cmts]) => {
        setActivity(acts);
        setComments(cmts);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [card?.id]);

  // Handle @mention query changes
  useEffect(() => {
    if (mentionQuery === null || mentionQuery === "") {
      setMentionUsers([]);
      return;
    }
    const t = setTimeout(() => {
      searchMentionUsers(mentionQuery)
        .then(setMentionUsers)
        .catch(() => setMentionUsers([]));
    }, 200);
    return () => clearTimeout(t);
  }, [mentionQuery]);

  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setCommentBody(val);
    // Detect @mention in progress
    const match = val.slice(0, e.target.selectionStart).match(/@(\w*)$/);
    setMentionQuery(match ? match[1] : null);
  }, []);

  const insertMention = useCallback(
    (user: MentionUser) => {
      const ta = textareaRef.current;
      if (!ta) return;
      const before = commentBody.slice(0, ta.selectionStart).replace(/@\w*$/, "");
      const after = commentBody.slice(ta.selectionStart);
      setCommentBody(`${before}@${user.full_name} ${after}`);
      setMentionedIds((prev) => [...new Set([...prev, user.id])]);
      setMentionQuery(null);
      setMentionUsers([]);
      ta.focus();
    },
    [commentBody]
  );

  const handleSend = useCallback(async () => {
    if (!card || !commentBody.trim()) return;
    setSending(true);
    try {
      const newComment = await addComment(card.id, commentBody.trim(), mentionedIds);
      setComments((prev) => [...prev, newComment]);
      setCommentBody("");
      setMentionedIds([]);
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
    }
  }, [card, commentBody, mentionedIds]);

  const handleUpdateComment = useCallback(
    async (comment: Comment) => {
      if (!card || !commentDraft.trim()) return;
      setCommentBusyId(comment.id);
      try {
        const updated = await updateComment(card.id, comment.id, commentDraft.trim(), comment.mentions);
        setComments((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
        setEditingCommentId(null);
        setCommentDraft("");
      } catch (err) {
        console.error(err);
      } finally {
        setCommentBusyId(null);
      }
    },
    [card, commentDraft],
  );

  const handleDeleteComment = useCallback(
    async (comment: Comment) => {
      if (!card) return;
      setCommentBusyId(comment.id);
      try {
        await deleteComment(card.id, comment.id);
        setComments((prev) => prev.filter((item) => item.id !== comment.id));
      } catch (err) {
        console.error(err);
      } finally {
        setCommentBusyId(null);
      }
    },
    [card],
  );

  // Send chat message
  const sendChatMessage = useCallback(async () => {
    if (!card || !chatInput.trim()) return;
    const userMessage = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const reader = await sendResumeChat(card.candidate.id, jobId || null, userMessage);
      const decoder = new TextDecoder();
      let assistantMessage = '';
      setChatMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        assistantMessage += decoder.decode(value, { stream: true });
        setChatMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, content: assistantMessage }];
          }
          return prev;
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setChatLoading(false);
    }
  }, [card, jobId, chatInput]);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const cfg = card ? STAGE_CONFIG[card.status as keyof typeof STAGE_CONFIG] : null;
  const candidateName = card ? getCandidateName(card.candidate) : "";
  const candidateEmail = card ? getCandidateEmail(card.candidate) : "";

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
          card ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      {/* Drawer panel */}
      <div
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col bg-slate-950 shadow-2xl shadow-black/60 transition-transform duration-300 ease-out ${
          card ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {!card ? null : (
          <>
            {/* Header */}
            <div
              className={`bg-gradient-to-r ${cfg?.bgGradient} border-b border-slate-800 px-6 py-5`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-base font-bold text-white shadow">
                    {getInitials(card.candidate)}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {candidateName}
                    </h2>
                    {card.candidate.headline && (
                      <p className="text-sm text-slate-400">{card.candidate.headline}</p>
                    )}
                    <p className="mt-0.5 text-xs text-slate-500">{candidateEmail}</p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Stage pill */}
              <div className="mt-4 flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${cfg?.color} ${cfg?.textColor} bg-slate-950/50`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${cfg?.dot}`} />
                  {cfg?.label}
                </span>
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="h-3 w-3" />
                  Applied {timeAgo(card.applied_at)}
                </span>
              </div>
            </div>

            {/* Tab bar */}
      <div className="flex border-b border-slate-800">
        {(["activity", "comments", "ai-chat"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 px-4 py-3 text-sm font-medium capitalize transition ${
              tab === t
                ? "border-b-2 border-cyan-400 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {t === "comments" ? `Comments (${comments.length})` : 
             t === "ai-chat" ? "AI Chat" : "Activity"}
          </button>
        ))}
      </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loading && (
                <div className="space-y-3">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="h-14 animate-pulse rounded-2xl bg-slate-800/50" />
                  ))}
                </div>
              )}

              {/* Activity Timeline */}
              {!loading && tab === "activity" && (
                <div className="relative space-y-0">
                  {/* Vertical line */}
                  {activity.length > 0 && (
                    <div className="absolute left-[17px] top-5 bottom-5 w-px bg-slate-800" />
                  )}

                  {activity.length === 0 && (
                    <p className="text-center text-sm text-slate-500 pt-8">No activity yet.</p>
                  )}

                  {activity.map((act, i) => (
                    <div key={act.id} className="relative flex gap-4 pb-5">
                      {/* Timeline dot */}
                      <div className="relative z-10 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-slate-800 border border-slate-700 text-slate-400">
                        {actionIcon(act.action)}
                      </div>
                      {/* Content */}
                      <div className="flex-1 pt-1">
                        <p className="text-sm text-white leading-snug">
                          {act.details ?? act.action}
                        </p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                          <User className="h-3 w-3" />
                          <span>{act.author_name ?? "System"}</span>
                          <span>·</span>
                          <span>{timeAgo(act.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Comments */}
              {!loading && tab === "comments" && (
                <div className="space-y-4">
                  {comments.length === 0 && (
                    <p className="text-center text-sm text-slate-500 pt-8">No comments yet. Be the first!</p>
                  )}
                  {comments.map((c) => (
                    <div key={c.id} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 text-xs font-bold text-white">
                          {c.author_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-sm font-medium text-white">{c.author_name}</span>
                        <span className="ml-auto text-xs text-slate-500">{timeAgo(c.created_at)}</span>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingCommentId(c.id);
                            setCommentDraft(c.body);
                          }}
                          className="rounded-full p-1 text-slate-500 transition hover:bg-slate-800 hover:text-cyan-300"
                          title="Edit comment"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteComment(c)}
                          disabled={commentBusyId === c.id}
                          className="rounded-full p-1 text-slate-500 transition hover:bg-slate-800 hover:text-rose-300 disabled:opacity-40"
                          title="Delete comment"
                        >
                          {commentBusyId === c.id ? <Clock className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                      {editingCommentId === c.id ? (
                        <div className="space-y-2">
                          <textarea
                            value={commentDraft}
                            onChange={(event) => setCommentDraft(event.target.value)}
                            rows={3}
                            className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                          />
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingCommentId(null);
                                setCommentDraft("");
                              }}
                              className="inline-flex items-center gap-1 rounded-full border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500"
                            >
                              <X className="h-3.5 w-3.5" />
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => handleUpdateComment(c)}
                              disabled={commentBusyId === c.id || !commentDraft.trim()}
                              className="inline-flex items-center gap-1 rounded-full bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-40"
                            >
                              <Check className="h-3.5 w-3.5" />
                              Save
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{c.body}</p>
                      )}
                      {c.mentions.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {c.mentions.map((mid) => (
                            <span key={mid} className="rounded-full bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-400 border border-cyan-800">
                              @{mid}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* AI Chat */}
              {!loading && tab === "ai-chat" && (
                <div className="flex h-full flex-col">
                  <div className="flex-1 overflow-y-auto space-y-4">
                    {chatMessages.length === 0 && (
                      <div className="flex h-full flex-col items-center justify-center text-center pt-8">
                        <div className="mb-4 h-12 w-12 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                          <MessageSquare className="h-6 w-6 text-white" />
                        </div>
                        <p className="text-sm text-slate-400 mb-4">Ask me anything about this candidate!</p>
                        <div className="flex flex-wrap gap-2 justify-center">
                          {["Summarize this candidate", "What are their strengths?", "Generate interview questions"].map((q) => (
                            <button
                              key={q}
                              onClick={() => { setChatInput(q); }}
                              className="px-3 py-1.5 text-xs rounded-full border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {chatMessages.map((msg, i) => (
                      <div
                        key={i}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                            msg.role === 'user'
                              ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white'
                              : 'bg-slate-800 text-slate-200'
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="bg-slate-800 rounded-2xl px-4 py-3 text-sm text-slate-200">
                          <span className="animate-pulse">Thinking…</span>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                </div>
              )}
            </div>

            {/* Comment composer (only on comments tab) */}
            {tab === "comments" && (
              <div className="border-t border-slate-800 px-6 py-4">
                <div className="relative">
                  <textarea
                    ref={textareaRef}
                    value={commentBody}
                    onChange={handleTextChange}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder="Add a comment… Use @name to mention a teammate"
                    rows={3}
                    className="w-full resize-none rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition"
                  />

                  {/* Mention dropdown */}
                  {mentionUsers.length > 0 && (
                    <div className="absolute bottom-full mb-1 left-0 w-full rounded-2xl border border-slate-700 bg-slate-900 shadow-xl z-10">
                      {mentionUsers.map((u) => (
                        <button
                          key={u.id}
                          onMouseDown={(e) => { e.preventDefault(); insertMention(u); }}
                          className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-slate-200 hover:bg-slate-800 first:rounded-t-2xl last:rounded-b-2xl"
                        >
                          <div className="h-6 w-6 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white">
                            {u.full_name.charAt(0)}
                          </div>
                          <div>
                            <span className="font-medium">{u.full_name}</span>
                            <span className="ml-2 text-xs text-slate-500">{u.email}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-2 flex items-center justify-between">
                  <p className="text-[11px] text-slate-600">⌘ + Enter to send</p>
                  <button
                    onClick={handleSend}
                    disabled={!commentBody.trim() || sending}
                    className="inline-flex items-center gap-2 rounded-full bg-cyan-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Send className="h-3.5 w-3.5" />
                    {sending ? "Sending…" : "Send"}
                  </button>
                </div>
              </div>
            )}

            {/* Chat composer (only on ai-chat tab) */}
            {tab === "ai-chat" && (
              <div className="border-t border-slate-800 px-6 py-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        sendChatMessage();
                      }
                    }}
                    placeholder="Ask about this candidate…"
                    className="flex-1 rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition"
                  />
                  <button
                    onClick={sendChatMessage}
                    disabled={!chatInput.trim() || chatLoading}
                    className="rounded-full bg-cyan-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-40"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
