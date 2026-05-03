import type { LessonVideo } from './lesson'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'


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
  reference_answer?: string
}

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

export type InteractiveTickParams = {
  session_id: string
  message?: string
  action?: 'confirm_yes' | 'confirm_not_yet'
  widget_result?: Record<string, unknown>
}


async function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
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

export async function startInteractiveLesson(
  lessonId: string,
  persona: string,
  course?: string,
): Promise<InteractiveSessionState> {
  return postJson<InteractiveSessionState>('/lesson/interactive/start', {
    lesson_id: lessonId,
    persona,
    course: course ?? null,
  })
}

export async function getInteractiveSession(sessionId: string): Promise<InteractiveSessionState> {
  const res = await fetch(`${API_URL}/lesson/interactive/session/${sessionId}`)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `session fetch failed: ${res.status}`)
  }
  return res.json()
}

export async function continueInteractiveSession(sessionId: string): Promise<InteractiveSessionState> {
  return getInteractiveSession(sessionId)
}

export async function tickInteractiveLesson(params: InteractiveTickParams): Promise<InteractiveSessionState> {
  return postJson<InteractiveSessionState>('/lesson/interactive/tick', {
    session_id: params.session_id,
    message: params.message,
    action: params.action,
    widget_result: params.widget_result,
  })
}

export async function scoreLesson(params: {
  lessonId: string
  persona: string
  response: string
  question?: string
  referenceAnswer?: string
  explicitScore?: number
}): Promise<void> {
  await postJson<unknown>('/lesson/score', {
    lesson_id: params.lessonId,
    persona: params.persona,
    response: params.response,
    question: params.question ?? null,
    reference_answer: params.referenceAnswer ?? null,
    explicit_score: params.explicitScore ?? null,
  })
}

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
