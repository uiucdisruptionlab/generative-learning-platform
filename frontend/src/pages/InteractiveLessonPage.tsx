import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { usePersona } from '../contexts/PersonaContext'
import {
  startInteractiveLesson,
  continueInteractiveSession,
  tickInteractiveLesson,
  type InteractiveSessionState,
  type InteractiveTranscriptEntry,
  type PendingWidget,
  type VideoWidgetPayload,
} from '../api/interactiveLesson'
import type { LessonVideo } from '../api/lesson'

function VideoCard({ video }: { video: LessonVideo }) {
  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-3 hover:border-primary/50 transition-colors"
    >
      <img src={video.thumbnail} alt={video.title} className="w-24 h-16 rounded-lg object-cover flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-900 dark:text-white line-clamp-2">{video.title}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{video.channel}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 line-clamp-2">{video.reason}</p>
      </div>
    </a>
  )
}

function McqWidget({
  payload,
  disabled,
  onSubmit,
}: {
  payload: Extract<PendingWidget, { type: 'mcq' }>['payload']
  disabled: boolean
  onSubmit: (result: Record<string, unknown>) => void
}) {
  const [idx, setIdx] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [sent, setSent] = useState(false)
  const opts = payload.options ?? []
  const correct = Math.min(Math.max(0, payload.correct_index ?? 0), Math.max(0, opts.length - 1))

  const check = () => {
    if (idx === null || revealed || disabled) return
    setRevealed(true)
  }

  const finish = () => {
    if (idx === null || sent || disabled) return
    setSent(true)
    onSubmit({
      selected_index: idx,
      selected_option: opts[idx] ?? '',
      correct_index: correct,
      correct_option: opts[correct] ?? '',
      correct: idx === correct,
      question: payload.question,
    })
  }

  return (
    <div className="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/90 p-5 space-y-3">
      <p className="text-sm font-semibold text-slate-900 dark:text-white">{payload.question}</p>
      <div className="space-y-2">
        {opts.map((opt, i) => {
          const selected = idx === i
          const show = revealed
          const isCorrect = i === correct
          return (
            <button
              key={i}
              type="button"
              disabled={revealed || disabled}
              onClick={() => setIdx(i)}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition-all ${
                show && isCorrect
                  ? 'border-primary bg-emerald-50 dark:bg-emerald-900/20'
                  : show && selected && !isCorrect
                  ? 'border-red-400 bg-red-50 dark:bg-red-900/20'
                  : selected
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/40'
              }`}
            >
              {opt}
            </button>
          )
        })}
      </div>
      {!revealed && (
        <button
          type="button"
          disabled={disabled || idx === null}
          onClick={check}
          className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40"
        >
          Check answer
        </button>
      )}
      {revealed && payload.explanation && (
        <p className="text-xs text-slate-600 dark:text-slate-400">{payload.explanation}</p>
      )}
      {revealed && !sent && (
        <button
          type="button"
          disabled={disabled}
          onClick={finish}
          className="px-4 py-2 rounded-xl border-2 border-primary text-primary text-sm font-semibold"
        >
          Continue
        </button>
      )}
    </div>
  )
}

function FlashcardsWidget({
  payload,
  disabled,
  onSubmit,
}: {
  payload: Extract<PendingWidget, { type: 'flashcards' }>['payload']
  disabled: boolean
  onSubmit: (result: Record<string, unknown>) => void
}) {
  const cards =
    payload.cards && payload.cards.length > 0
      ? payload.cards
      : (payload.concepts ?? []).map((c) => ({
          front: c.name,
          back: c.description ?? '—',
        }))
  const [i, setI] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [reviewed, setReviewed] = useState(false)

  if (!cards.length) {
    return <p className="text-sm text-slate-500">No flashcard content provided.</p>
  }

  const card = cards[Math.min(i, cards.length - 1)]

  return (
    <div className="rounded-2xl border-2 border-amber-200/80 dark:border-amber-800/40 bg-amber-50/40 dark:bg-amber-950/20 p-5 space-y-4">
      <p className="text-xs font-semibold text-amber-800 dark:text-amber-200 uppercase tracking-wide">
        Flashcards · {i + 1} / {cards.length}
      </p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setFlipped(!flipped)}
        className="w-full min-h-[140px] rounded-xl border-2 border-amber-300/60 dark:border-amber-700/50 bg-white dark:bg-slate-900 p-4 text-left transition-transform hover:scale-[1.01]"
      >
        <p className="text-xs text-slate-500 mb-1">{flipped ? 'Back' : 'Front'}</p>
        <p className="text-slate-900 dark:text-white font-medium whitespace-pre-wrap">{flipped ? card.back : card.front}</p>
        <p className="text-xs text-slate-400 mt-3">Tap to flip</p>
      </button>
      <div className="flex gap-2 flex-wrap">
        <button
          type="button"
          disabled={disabled || i === 0}
          onClick={() => {
            setI((x) => Math.max(0, x - 1))
            setFlipped(false)
          }}
          className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 text-sm disabled:opacity-40"
        >
          Prev
        </button>
        <button
          type="button"
          disabled={disabled || i >= cards.length - 1}
          onClick={() => {
            setI((x) => Math.min(cards.length - 1, x + 1))
            setFlipped(false)
          }}
          className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 text-sm disabled:opacity-40"
        >
          Next
        </button>
        <button
          type="button"
          disabled={disabled || reviewed}
          onClick={() => {
            setReviewed(true)
            onSubmit({ cards_viewed: cards.length, acknowledged: true })
          }}
          className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-semibold disabled:opacity-40"
        >
          Done reviewing
        </button>
      </div>
    </div>
  )
}

function FreeResponseWidget({
  payload,
  disabled,
  onSubmit,
}: {
  payload: Extract<PendingWidget, { type: 'free_response' }>['payload']
  disabled: boolean
  onSubmit: (result: Record<string, unknown>) => void
}) {
  const [text, setText] = useState('')
  const [sent, setSent] = useState(false)

  return (
    <div className="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/90 p-5 space-y-3">
      <p className="text-sm font-medium text-slate-900 dark:text-white">{payload.question}</p>
      <textarea
        value={text}
        disabled={disabled || sent}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        className="w-full rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
        placeholder="Type your answer…"
      />
      <button
        type="button"
        disabled={disabled || sent || !text.trim()}
        onClick={() => {
          setSent(true)
          onSubmit({ text: text.trim() })
        }}
        className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40"
      >
        Submit
      </button>
    </div>
  )
}

function youtubeEmbedSrc(watchUrl: string): string | null {
  try {
    const u = new URL(watchUrl)
    if (u.hostname === 'youtu.be') {
      const id = u.pathname.replace(/^\//, '').split('/')[0]
      return id ? `https://www.youtube.com/embed/${id}` : null
    }
    if (u.hostname.includes('youtube.com')) {
      const v = u.searchParams.get('v')
      if (v) return `https://www.youtube.com/embed/${v}`
    }
  } catch {
    return null
  }
  return null
}

function VideoRecommendWidget({
  payload,
  disabled,
  onSubmit,
}: {
  payload: VideoWidgetPayload
  disabled: boolean
  onSubmit: (result: Record<string, unknown>) => void
}) {
  const embed = payload.url ? youtubeEmbedSrc(payload.url) : null
  const videoForCard: LessonVideo = {
    title: payload.title || 'Video',
    url: payload.url,
    channel: payload.channel,
    thumbnail: payload.thumbnail,
    reason: payload.reason,
  }

  return (
    <div className="rounded-2xl border-2 border-red-200/60 dark:border-red-900/50 bg-white/95 dark:bg-slate-900/95 p-5 space-y-4 shadow-soft">
      <p className="text-xs font-bold uppercase tracking-wide text-red-800 dark:text-red-200 flex items-center gap-2">
        <span className="material-symbols-outlined text-lg">smart_display</span>
        Video for this checkpoint
      </p>
      {payload.reason && (
        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">{payload.reason}</p>
      )}
      {payload.search_query_used && (
        <p className="text-xs text-slate-500 font-mono">Search: {payload.search_query_used}</p>
      )}
      {embed ? (
        <div className="aspect-video w-full max-w-[720px] rounded-xl overflow-hidden border-2 border-slate-200 dark:border-slate-700 bg-black shadow-inner">
          <iframe
            title={payload.title || 'YouTube video'}
            src={embed}
            className="h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      ) : payload.url ? (
        <VideoCard video={videoForCard} />
      ) : (
        <p className="text-sm text-amber-800 dark:text-amber-200 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50/80 dark:bg-amber-950/40 px-3 py-2">
          Couldn&apos;t load a watch link. Set <code className="text-xs">YOUTUBE_API_KEY</code> in{' '}
          <code className="text-xs">backend/.env</code> and restart the server, then try again.
        </p>
      )}
      {payload.url && !embed && (
        <a
          href={payload.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
        >
          Open in YouTube
          <span className="material-symbols-outlined text-base">open_in_new</span>
        </a>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSubmit({ continued: true })}
        className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40"
      >
        Continue
      </button>
    </div>
  )
}

function stepBadge(stepType: string): { label: string; icon: string; color: string } {
  if (stepType === 'example') {
    return {
      label: 'Example',
      icon: 'lightbulb',
      color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20',
    }
  }
  if (stepType === 'summary') {
    return {
      label: 'Summary',
      icon: 'summarize',
      color: 'text-primary bg-emerald-50 dark:bg-emerald-900/20',
    }
  }
  return {
    label: 'Concept',
    icon: 'school',
    color: 'text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800',
  }
}

function UserTurn({ content }: { content: string }) {
  if (content === '[Learner: ready to continue]') {
    return (
      <div className="flex justify-center py-1">
        <span className="text-xs font-medium px-3 py-1.5 rounded-full bg-slate-200/90 dark:bg-slate-700/90 text-slate-600 dark:text-slate-300">
          You moved on
        </span>
      </div>
    )
  }
  if (content.startsWith('[Completed activity:')) {
    return (
      <div className="flex justify-center py-1">
        <span className="text-xs font-medium px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-primary border border-primary/20">
          Activity completed
        </span>
      </div>
    )
  }
  return (
    <div className="flex justify-end">
      <div className="max-w-[min(100%,520px)] rounded-2xl rounded-br-md border-2 border-primary/25 bg-white dark:bg-slate-900/90 px-5 py-4 shadow-soft">
        <p className="text-xs font-bold uppercase tracking-wide text-primary mb-2">You</p>
        <p className="text-sm text-slate-800 dark:text-slate-100 leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  )
}

function TranscriptBlock({ entry }: { entry: InteractiveTranscriptEntry }) {
  const meta = entry.meta ?? {}
  const kind = typeof meta.kind === 'string' ? meta.kind : undefined

  if (entry.role === 'user') {
    return <UserTurn content={entry.content} />
  }

  if (kind === 'overview') {
    return (
      <section className="rounded-2xl bg-primary/5 dark:bg-primary/10 border-2 border-primary/20 p-6 shadow-soft">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mb-4 text-primary bg-emerald-50 dark:bg-emerald-900/20`}
        >
          <span className="material-symbols-outlined text-sm">menu_book</span>
          Overview
        </span>
        <p className="text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{entry.content}</p>
      </section>
    )
  }

  if (kind === 'step') {
    const stepType = String(meta.step_type ?? 'concept')
    const title = String(meta.title ?? '')
    const body = String(meta.content ?? '')
    const badge = stepBadge(stepType)
    const borderColor =
      stepType === 'example'
        ? 'border-amber-200/80 dark:border-amber-800/40'
        : stepType === 'summary'
          ? 'border-primary/30 dark:border-primary/20'
          : 'border-slate-200 dark:border-slate-700'
    return (
      <section
        className={`rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 ${borderColor} shadow-soft`}
      >
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mb-3 ${badge.color}`}>
          <span className="material-symbols-outlined text-sm">{badge.icon}</span>
          {badge.label}
        </span>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">{title}</h3>
        <p className="text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">{body}</p>
      </section>
    )
  }

  if (kind === 'engage') {
    return (
      <section className="rounded-2xl border-2 border-indigo-200/70 dark:border-indigo-800/50 bg-indigo-50/40 dark:bg-indigo-950/30 p-6 shadow-soft">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-300">psychology</span>
          <span className="text-xs font-bold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">
            Tutor follow-up
          </span>
        </div>
        <p className="text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{entry.content}</p>
      </section>
    )
  }

  if (kind === 'closing') {
    return (
      <section className="rounded-2xl border-2 border-emerald-200/80 dark:border-emerald-800/40 bg-emerald-50/50 dark:bg-emerald-950/25 p-6 shadow-soft">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-primary">celebration</span>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Wrap-up</h3>
        </div>
        <p className="text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">{entry.content}</p>
      </section>
    )
  }

  if (kind === 'widget_enqueue') {
    return (
      <p className="text-xs text-slate-500 dark:text-slate-400 italic px-1">{entry.content}</p>
    )
  }

  return (
    <section className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/60 p-5">
      <p className="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">{entry.content}</p>
    </section>
  )
}

function normalizePendingWidget(raw: unknown): PendingWidget | null {
  if (!raw || typeof raw !== 'object') return null
  const w = raw as { type?: string; payload?: unknown }
  const t = (w.type ?? '').toLowerCase()
  const p = w.payload && typeof w.payload === 'object' ? (w.payload as Record<string, unknown>) : {}
  if (t === 'mcq') {
    const options = Array.isArray(p.options) ? (p.options as string[]) : []
    return {
      type: 'mcq',
      payload: {
        question: String(p.question ?? ''),
        options: options.length ? options : ['A', 'B', 'C', 'D'],
        correct_index: Number.isFinite(Number(p.correct_index)) ? Number(p.correct_index) : 0,
        explanation: String(p.explanation ?? ''),
      },
    }
  }
  if (t === 'flashcards') {
    const concepts = Array.isArray(p.concepts)
      ? (p.concepts as { name: string; description?: string }[])
      : []
    const cards = Array.isArray(p.cards) ? (p.cards as { front: string; back: string }[]) : undefined
    return { type: 'flashcards', payload: { concepts, cards } }
  }
  if (t === 'free_response') {
    return { type: 'free_response', payload: { question: String(p.question ?? '') } }
  }
  if (t === 'video') {
    return {
      type: 'video',
      payload: {
        title: String(p.title ?? ''),
        url: String(p.url ?? ''),
        channel: String(p.channel ?? ''),
        thumbnail: String(p.thumbnail ?? ''),
        reason: String(p.reason ?? ''),
        source: p.source != null ? String(p.source) : undefined,
        search_query_used: p.search_query_used != null ? String(p.search_query_used) : undefined,
        search_query_attempted: p.search_query_attempted != null ? String(p.search_query_attempted) : undefined,
      },
    }
  }
  return null
}

export default function InteractiveLessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>()
  const [searchParams] = useSearchParams()
  const courseOverride = searchParams.get('course') ?? undefined
  const sessionOverride = searchParams.get('session_id') ?? undefined
  const { currentPersona } = usePersona()
  const persona = currentPersona === 'demo' ? 'charles' : currentPersona

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [state, setState] = useState<InteractiveSessionState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [state?.transcript.length, state?.pending_widget])

  const runTick = useCallback(
    async (params: { message?: string; action?: 'confirm_yes' | 'confirm_not_yet'; widget_result?: Record<string, unknown> }) => {
      if (!state?.session_id) return
      setBusy(true)
      setError(null)
      try {
        const next = await tickInteractiveLesson({
          session_id: state.session_id,
          ...params,
        })
        setState({ ...next, pending_widget: normalizePendingWidget(next.pending_widget as unknown) })
        setDraft('')
      } catch (e) {
        setError(String(e))
      } finally {
        setBusy(false)
      }
    },
    [state?.session_id],
  )

  useEffect(() => {
    if (!lessonId && !sessionOverride) return
    let cancelled = false
    setLoading(true)
    setError(null)
    const load = sessionOverride
      ? continueInteractiveSession(sessionOverride)
      : startInteractiveLesson(lessonId, persona, courseOverride)
    load
      .then((s) => {
        if (!cancelled) setState({ ...s, pending_widget: normalizePendingWidget(s.pending_widget) })
      })
      .catch((e) => {
        if (!cancelled) setError(String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lessonId, persona, courseOverride, sessionOverride])

  const pending = state ? normalizePendingWidget(state.pending_widget as unknown) : null

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title={state?.lesson_title ?? 'Interactive lesson'}
      description="Step-by-step tutor with checks · same sources as the full lesson (readings + YouTube)."
      action={
        lessonId ? (
          <Link
            to={`/lesson/${lessonId}${courseOverride ? `?course=${encodeURIComponent(courseOverride)}` : ''}`}
            className="text-sm text-primary hover:underline"
          >
            Classic lesson view
          </Link>
        ) : null
      }
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-32 min-w-0">
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-24 text-gray-400">
            <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            <p className="text-sm">Starting interactive session (loading sources + overview)…</p>
          </div>
        ) : state ? (
          <div className="space-y-8">
            {state.video_status?.source === 'lesson_cache' && state.video_status.detail && (
              <div className="rounded-xl border border-amber-200/80 dark:border-amber-800/50 bg-amber-50/60 dark:bg-amber-950/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
                <span className="material-symbols-outlined align-middle text-base mr-1">info</span>
                {state.video_status.detail}
              </div>
            )}

            {state.video_status?.source === 'none' && state.video_status.detail && (
              <div className="rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
                <p className="font-semibold text-slate-900 dark:text-white mb-1 flex items-center gap-2">
                  <span className="material-symbols-outlined text-slate-500 text-lg">video_library</span>
                  No related videos yet
                </p>
                <p>{state.video_status.detail}</p>
              </div>
            )}

            {state.chunks_status?.detail && state.chunks_status.status && state.chunks_status.status !== 'ok' && (
              <div className="rounded-xl border border-sky-200/80 dark:border-sky-800/50 bg-sky-50/70 dark:bg-sky-950/30 px-4 py-3 text-sm text-sky-900 dark:text-sky-100">
                <p className="font-semibold flex items-center gap-2 mb-1">
                  <span className="material-symbols-outlined text-lg">article</span>
                  Lecture excerpts (Pinecone)
                </p>
                <p className="text-sky-900/90 dark:text-sky-200/90">{state.chunks_status.detail}</p>
                {(state.chunks_status.requested_ids ?? 0) > 0 && (
                  <p className="text-xs mt-2 opacity-90 font-mono">
                    Loaded {state.chunks_status.loaded_segments ?? 0} / {state.chunks_status.requested_ids} segments
                    {state.chunks_status.namespace != null && state.chunks_status.namespace !== ''
                      ? ` · namespace “${state.chunks_status.namespace}”`
                      : ''}
                    {state.chunks_status.index ? ` · index “${state.chunks_status.index}”` : ''}
                  </p>
                )}
                {state.chunks_status.missing_ids_sample && state.chunks_status.missing_ids_sample.length > 0 && (
                  <p className="text-xs mt-1 opacity-80">
                    Example IDs with no text: {state.chunks_status.missing_ids_sample.join(', ')}
                  </p>
                )}
                {state.chunks_status.namespaces_tried && state.chunks_status.namespaces_tried.length > 0 && (
                  <p className="text-xs mt-1 opacity-80">
                    Namespaces tried: {state.chunks_status.namespaces_tried.join(', ')}
                  </p>
                )}
              </div>
            )}

            {state.videos.length > 0 && (
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-2xl">play_circle</span>
                  Related videos
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 -mt-1">
                  {state.video_status?.source === 'youtube'
                    ? 'From YouTube Data API for this lesson topic (same pipeline as the classic generated lesson).'
                    : 'From your saved generated lesson on disk.'}
                </p>
                {state.videos.map((v, i) => (
                  <VideoCard key={i} video={v} />
                ))}
              </section>
            )}

            <section className="space-y-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">route</span>
                Your walkthrough
              </h3>
              {state.transcript.map((entry, idx) => (
                <TranscriptBlock key={idx} entry={entry} />
              ))}
              <div ref={bottomRef} />
            </section>

            {pending && state.awaiting === 'widget' && (
              <div className="space-y-3">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
                  <span className="material-symbols-outlined text-amber-600 dark:text-amber-400 text-2xl">quiz</span>
                  Quick check
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 -mt-1">
                  Quiz, flashcards, video, or short answer — chosen for this point in the lesson.
                </p>
                {pending.type === 'mcq' && (
                  <McqWidget
                    payload={pending.payload}
                    disabled={busy}
                    onSubmit={(widget_result) => runTick({ widget_result })}
                  />
                )}
                {pending.type === 'flashcards' && (
                  <FlashcardsWidget
                    payload={pending.payload}
                    disabled={busy}
                    onSubmit={(widget_result) => runTick({ widget_result })}
                  />
                )}
                {pending.type === 'free_response' && (
                  <FreeResponseWidget
                    payload={pending.payload}
                    disabled={busy}
                    onSubmit={(widget_result) => runTick({ widget_result })}
                  />
                )}
                {pending.type === 'video' && (
                  <VideoRecommendWidget
                    payload={pending.payload}
                    disabled={busy}
                    onSubmit={(widget_result) => runTick({ widget_result })}
                  />
                )}
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => runTick({ action: 'confirm_yes' })}
                  className="text-xs text-slate-500 underline hover:text-primary disabled:opacity-40"
                >
                  Skip this activity
                </button>
              </div>
            )}

            {state.awaiting === 'confirm' && (
              <section className="rounded-2xl border-2 border-dashed border-primary/30 bg-primary/5 dark:bg-primary/10 px-5 py-5 space-y-3">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">touch_app</span>
                  Checkpoint
                </p>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Respond naturally: say you&apos;re ready to continue, ask for clarification, or say you&apos;re done.
                </p>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={2}
                  disabled={busy}
                  placeholder="e.g., “continue”, “can you explain that again?”, or “i'm done for now”"
                  className="w-full rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
                />
                <button
                  type="button"
                  disabled={busy || !draft.trim()}
                  onClick={() => runTick({ message: draft })}
                  className="px-5 py-2 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40"
                >
                  Send
                </button>
              </section>
            )}

            {state.awaiting === 'text' && (
              <section className="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/90 p-5 space-y-3 shadow-soft">
                <label className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-slate-500">edit_note</span>
                  Your turn — reflect or ask
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Reply in your own words so the tutor can respond and may offer a quick activity.
                </p>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={3}
                  disabled={busy}
                  placeholder="Does this make sense? What feels fuzzy?"
                  className="w-full rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
                />
                <button
                  type="button"
                  disabled={busy || !draft.trim()}
                  onClick={() => runTick({ message: draft })}
                  className="px-5 py-2 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40"
                >
                  Send
                </button>
              </section>
            )}

            {state.awaiting === 'none' && (
              <p className="text-sm text-slate-600 dark:text-slate-400">
                You&apos;re at the end of this walkthrough. Reopen from the roadmap to run it again, or switch to the{' '}
                <Link className="text-primary underline" to={lessonId ? `/lesson/${lessonId}?course=${courseOverride ?? ''}` : '/roadmap'}>
                  generated lesson
                </Link>
                .
              </p>
            )}

            {import.meta.env.DEV && (
              <p className="text-xs text-slate-400 font-mono">stage: {state.stage}</p>
            )}
          </div>
        ) : null}
      </div>
    </AppLayout>
  )
}
