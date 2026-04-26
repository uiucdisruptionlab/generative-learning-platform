import type { LessonVideo } from './lesson'
import { studentIdForPersona } from '../auth/studentIdentity'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const PERSONA_COURSES: Record<string, string> = {
  alice: 'python',
  bob: 'financing',
  charles: 'accounting',
  demo: 'accounting',
}

export type InteractiveAwaiting = 'confirm' | 'text' | 'widget' | 'none'

export type InteractiveTranscriptEntry = {
  role: 'user' | 'assistant'
  content: string
  meta?: Record<string, unknown>
}

export type McqWidgetPayload = {
  question: string
  options: string[]
  correct_index: number
  explanation: string
}

export type FlashcardsWidgetPayload = {
  concepts?: { name: string; description?: string }[]
  cards?: { front: string; back: string }[]
}

export type FreeResponseWidgetPayload = {
  question: string
}

/** Resolved on the server via YouTube Data API or a direct watch URL. */
export type VideoWidgetPayload = {
  title: string
  url: string
  channel: string
  thumbnail: string
  reason: string
  caption?: string
  source?: string
  search_query_used?: string
  search_query_attempted?: string
}

export type PendingWidget =
  | { type: 'mcq'; payload: McqWidgetPayload }
  | { type: 'flashcards'; payload: FlashcardsWidgetPayload }
  | { type: 'free_response'; payload: FreeResponseWidgetPayload }
  | { type: 'video'; payload: VideoWidgetPayload }

export type VideoStatus = {
  source: 'youtube' | 'lesson_cache' | 'none'
  detail: string | null
}

export type ChunksStatus = {
  status?: string
  detail?: string | null
  requested_ids?: number
  loaded_segments?: number
  namespace?: string
  index?: string
  missing_ids_sample?: string[]
  namespaces_tried?: string[]
}

export type InteractiveSessionState = {
  session_id: string
  stage: string
  lesson_title: string
  concepts: { name: string; description?: string }[]
  videos: LessonVideo[]
  video_status?: VideoStatus
  chunks_status?: ChunksStatus
  transcript: InteractiveTranscriptEntry[]
  pending_widget: PendingWidget | null
  awaiting: InteractiveAwaiting
  model_id: string
}

type AdaptiveConcept = {
  id?: string
  name?: string
  description?: string
}

type AdaptiveResponse = {
  action?: 'render_block' | 'knowledge_check' | 'reply' | 'complete' | 'advance' | 'retry'
  session_id: string
  student_id?: string
  mode?: string
  node_id?: string
  concept?: AdaptiveConcept
  block_index?: number
  blocks_per_concept?: number
  attempt_count?: number
  transcript?: InteractiveTranscriptEntry[]
  type?: 'video' | 'flashcard' | 'mcq'
  content?: Record<string, unknown>
  reply?: string
  score?: number
}

function resolveCourse(persona: string, course?: string): string | undefined {
  return course ?? PERSONA_COURSES[persona]
}

function correctIndex(content: Record<string, unknown>): number {
  const correct = String(content.correct ?? 'A').trim().toUpperCase()
  if (/^[A-D]$/.test(correct)) return correct.charCodeAt(0) - 65
  const asNumber = Number(correct)
  return Number.isFinite(asNumber) ? Math.max(0, asNumber) : 0
}

function blockToWidget(type?: AdaptiveResponse['type'], content: Record<string, unknown> = {}): PendingWidget | null {
  if (type === 'mcq') {
    const options = Array.isArray(content.options) ? content.options.map(String) : []
    return {
      type: 'mcq',
      payload: {
        question: String(content.question ?? ''),
        options: options.length ? options : ['A. Option A', 'B. Option B', 'C. Option C', 'D. Option D'],
        correct_index: correctIndex(content),
        explanation: String(content.explanation ?? ''),
      },
    }
  }
  if (type === 'flashcard') {
    return {
      type: 'flashcards',
      payload: {
        cards: [
          {
            front: String(content.front ?? ''),
            back: String(content.back ?? ''),
          },
        ],
      },
    }
  }
  if (type === 'video') {
    const searchQuery = String(content.search_query ?? '')
    return {
      type: 'video',
      payload: {
        title: searchQuery || 'Recommended YouTube search',
        url: '',
        channel: 'YouTube',
        thumbnail: '',
        reason: String(content.why ?? ''),
        search_query_attempted: searchQuery,
      },
    }
  }
  return null
}

function mapAdaptiveState(response: AdaptiveResponse): InteractiveSessionState {
  const conceptName = response.concept?.name ?? response.node_id ?? 'Adaptive lesson'
  const pending = response.action === 'render_block' ? blockToWidget(response.type, response.content) : null
  const awaiting: InteractiveAwaiting =
    response.action === 'render_block'
      ? 'widget'
      : response.action === 'knowledge_check' || response.action === 'reply'
        ? 'text'
        : response.action === 'complete' || response.action === 'advance'
          ? 'none'
          : 'confirm'

  return {
    session_id: response.session_id,
    stage: response.action ?? response.mode ?? 'adaptive',
    lesson_title: conceptName,
    concepts: response.concept
      ? [{ name: conceptName, description: response.concept.description }]
      : [],
    videos: [],
    transcript: response.transcript ?? [],
    pending_widget: pending,
    awaiting,
    model_id: 'bedrock',
  }
}

async function postAdaptive<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `${path} failed: ${res.status}`)
  }
  return res.json()
}

async function nextAdaptiveBlock(sessionId: string): Promise<InteractiveSessionState> {
  const block = await postAdaptive<AdaptiveResponse>('/lesson/block', { session_id: sessionId })
  if (block.action === 'knowledge_check') {
    const opened = await postAdaptive<AdaptiveResponse>('/lesson/message', { session_id: sessionId, message: '' })
    return mapAdaptiveState(opened)
  }
  return mapAdaptiveState(block)
}

export async function continueInteractiveSession(sessionId: string): Promise<InteractiveSessionState> {
  return nextAdaptiveBlock(sessionId)
}

export async function startInteractiveLesson(
  lessonId: string,
  persona: string,
  course?: string,
): Promise<InteractiveSessionState> {
  void lessonId
  const started = await postAdaptive<AdaptiveResponse>('/session/start', {
    student_id: studentIdForPersona(persona),
    course: resolveCourse(persona, course) ?? null,
  })
  return nextAdaptiveBlock(started.session_id)
}

export type InteractiveTickParams = {
  session_id: string
  message?: string
  action?: 'confirm_yes' | 'confirm_not_yet'
  widget_result?: Record<string, unknown>
}

export async function tickInteractiveLesson(params: InteractiveTickParams): Promise<InteractiveSessionState> {
  if (params.widget_result || params.action === 'confirm_yes') {
    return nextAdaptiveBlock(params.session_id)
  }
  const messaged = await postAdaptive<AdaptiveResponse>('/lesson/message', {
    session_id: params.session_id,
    message: params.message ?? '',
  })
  if (messaged.action === 'complete') {
    const completed = await postAdaptive<AdaptiveResponse>('/lesson/complete', {
      session_id: params.session_id,
    })
    if (completed.action === 'retry') {
      return nextAdaptiveBlock(params.session_id)
    }
    return mapAdaptiveState(completed)
  }
  return mapAdaptiveState(messaged)
}

export async function getInteractiveSession(sessionId: string): Promise<InteractiveSessionState> {
  const res = await fetch(`${API_URL}/lesson/interactive/session/${sessionId}`)
  if (!res.ok) throw new Error(`session fetch failed: ${res.status}`)
  return res.json()
}

/** Push MCQ / flashcards / free-response — same contract the model uses in `pending_widget`. */
export async function enqueueInteractiveWidget(
  sessionId: string,
  widget: { type: PendingWidget['type']; payload: Record<string, unknown> },
  note?: string,
): Promise<InteractiveSessionState> {
  const res = await fetch(`${API_URL}/lesson/interactive/widget`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      widget_type: widget.type,
      payload: widget.payload,
      note,
    }),
  })
  if (!res.ok) throw new Error(`enqueue widget failed: ${res.status}`)
  return res.json()
}
