import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { usePersona } from '../contexts/PersonaContext'
import {
  fetchLessonHistory,
  fetchLessonSession,
  type LessonSession,
  type LessonSessionSummary,
} from '../api/lessonHistory'

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function statusBadge(passed: boolean, score?: number | null): { label: string; className: string } {
  if (passed) {
    return {
      label: `Passed · ${score ?? '?'}/5`,
      className: 'bg-primary/10 dark:bg-primary/20 text-primary',
    }
  }
  return {
    label: `Retry · ${score ?? '?'}/5`,
    className: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  }
}

function MessageBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-primary text-white shadow-md shadow-primary/20'
            : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 ring-1 ring-slate-200 dark:ring-slate-700'
        }`}
      >
        {content}
      </div>
    </div>
  )
}

export default function LessonTranscriptPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { studentId: personaStudentId } = usePersona()
  const studentId = params.get('student_id') || personaStudentId
  const conceptId = params.get('concept_id') || ''
  const requestedSessionId = params.get('session_id') || ''

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [history, setHistory] = useState<LessonSessionSummary[]>([])
  const [active, setActive] = useState<LessonSession | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [loadingSession, setLoadingSession] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!studentId || !conceptId) {
      setLoadingHistory(false)
      return
    }
    let cancelled = false
    setLoadingHistory(true)
    setError(null)
    fetchLessonHistory(studentId, conceptId)
      .then((data) => {
        if (cancelled) return
        setHistory(data.sessions)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId, conceptId])

  // Pick the session to load: explicit ?session_id wins, else the most recent.
  const targetSessionId = useMemo(() => {
    if (requestedSessionId) return requestedSessionId
    return history[0]?.session_id ?? ''
  }, [requestedSessionId, history])

  useEffect(() => {
    if (!targetSessionId) {
      setActive(null)
      return
    }
    let cancelled = false
    setLoadingSession(true)
    setError(null)
    fetchLessonSession(targetSessionId)
      .then((data) => {
        if (!cancelled) setActive(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoadingSession(false)
      })
    return () => {
      cancelled = true
    }
  }, [targetSessionId])

  const conceptTitle = active?.concept_name || history[0]?.concept_name || conceptId || 'Past lesson'
  const description = active
    ? `${formatDate(active.completed_at)} · ${active.passed ? 'Passed' : 'Retry'}`
    : 'Read-only transcript of a past lesson'

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title={conceptTitle}
      description={description}
    >
      <div className="max-w-[1100px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        <div className="mb-6 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
          >
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to roadmap
          </button>
          {active && (
            <span
              className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${
                statusBadge(active.passed, active.score).className
              }`}
            >
              {statusBadge(active.passed, active.score).label}
            </span>
          )}
        </div>

        {error && (
          <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)] gap-6">
          <aside className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-industrial/45 dark:border-industrial/35 shadow-soft p-4 lg:sticky lg:top-8 self-start">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3 px-1">
              Past sessions
            </h2>
            {loadingHistory ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 px-1">Loading…</p>
            ) : history.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 px-1">
                No completed sessions for this concept yet.
              </p>
            ) : (
              <ul className="space-y-1">
                {history.map((session) => {
                  const isActive = session.session_id === targetSessionId
                  return (
                    <li key={session.session_id}>
                      <Link
                        to={`/lesson/transcript?student_id=${encodeURIComponent(studentId)}&concept_id=${encodeURIComponent(
                          conceptId,
                        )}&session_id=${encodeURIComponent(session.session_id)}`}
                        className={`block rounded-xl px-3 py-2 text-sm transition-colors ${
                          isActive
                            ? 'bg-primary/10 dark:bg-primary/20 text-primary font-semibold'
                            : 'text-slate-700 dark:text-slate-200 hover:bg-stone-100 dark:hover:bg-slate-800'
                        }`}
                      >
                        <div className="font-medium truncate">{formatDate(session.completed_at) || 'Unknown date'}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {session.passed ? 'Passed' : 'Retry'} · {session.score ?? '?'}/5
                        </div>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </aside>

          <main className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-industrial/45 dark:border-industrial/35 shadow-soft p-6 lg:p-8 min-w-0">
            {loadingSession ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400 dark:text-slate-500">
                <span className="material-symbols-outlined animate-spin text-3xl text-primary">progress_activity</span>
                <p className="text-sm">Loading transcript…</p>
              </div>
            ) : !active ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center text-slate-400 dark:text-slate-500">
                <span className="material-symbols-outlined text-3xl text-primary/60">forum</span>
                <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                  No transcript to show.
                </p>
                <p className="text-xs">
                  Complete this lesson once to start a history.
                </p>
              </div>
            ) : active.transcript.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400 dark:text-slate-500">
                <p className="text-sm">This session was completed without any messages.</p>
              </div>
            ) : (
              <div>
                {active.transcript.map((message, index) => (
                  <MessageBubble
                    key={index}
                    role={message.role}
                    content={message.content}
                  />
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </AppLayout>
  )
}
