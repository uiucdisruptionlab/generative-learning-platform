const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type TranscriptMessage = {
  role: 'user' | 'assistant' | string
  content: string
  meta?: Record<string, unknown> | null
}

export type LessonSessionSummary = {
  session_id: string
  student_id: string
  course_id: string
  lesson_id?: string | null
  concept_id: string
  concept_name?: string | null
  mode?: string | null
  score?: number | null
  passed: boolean
  started_at?: string | null
  completed_at: string
  metadata?: Record<string, unknown> | null
}

export type LessonSession = LessonSessionSummary & {
  transcript: TranscriptMessage[]
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchLessonHistory(
  studentId: string,
  conceptId?: string,
): Promise<{ student_id: string; concept_id: string | null; sessions: LessonSessionSummary[] }> {
  const params = new URLSearchParams()
  if (conceptId) params.set('concept_id', conceptId)
  const qs = params.toString()
  return getJson(`/lesson_history/${encodeURIComponent(studentId)}${qs ? `?${qs}` : ''}`)
}

export async function fetchLessonSession(sessionId: string): Promise<LessonSession> {
  return getJson(`/lesson_session/${encodeURIComponent(sessionId)}`)
}
