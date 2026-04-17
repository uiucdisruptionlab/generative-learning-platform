const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type LessonStep = {
  step_number: number
  title: string
  type: 'concept' | 'example' | 'summary'
  content: string
}

export type LessonVideo = {
  title: string
  url: string
  channel: string
  thumbnail: string
  reason: string
}

export type LessonQuestion = {
  type: 'multiple_choice' | 'fill_in_the_blank'
  question: string
  options?: string[]
  answer: string
  explanation: string
}

export type LessonConcept = {
  name: string
  description?: string
}

export type LessonContent = {
  lesson_id: string
  title: string
  overview: string
  steps: LessonStep[]
  videos: LessonVideo[]
  questions: LessonQuestion[]
  concepts?: LessonConcept[]
}

export async function fetchLesson(lessonId: string, persona: string, course?: string): Promise<LessonContent> {
  const params = new URLSearchParams({ persona })
  if (course) params.set('course', course)
  const res = await fetch(`${API_URL}/lesson/${lessonId}?${params.toString()}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch lesson: ${res.status}`)
  }
  return res.json()
}

export type LessonScoreRequest = {
  lesson_id: string
  response: string
  persona?: string
  student_id?: string
  course?: string
  question?: string
  reference_answer?: string
  rubric?: string
  metadata?: Record<string, unknown>
}

export type LessonScoreResponse = {
  student_id: string
  lesson_id: string
  course: string
  score: number
  passed: boolean
  explanation: string
  strengths: string[]
  gaps: string[]
  srs_record: Record<string, unknown>
  roadmap_progress: Record<string, unknown> | null
}

export async function scoreLessonResponse(payload: LessonScoreRequest): Promise<LessonScoreResponse> {
  const res = await fetch(`${API_URL}/lesson/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(`Failed to score lesson response: ${res.status}`)
  }
  return res.json()
}

export async function fetchDueReviews(persona: string, studentId?: string): Promise<{ student_id: string; due: Record<string, unknown>[]; review_mode: boolean }> {
  const params = new URLSearchParams({ persona })
  if (studentId) params.set('student_id', studentId)
  const res = await fetch(`${API_URL}/srs/due?${params.toString()}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch due reviews: ${res.status}`)
  }
  return res.json()
}

export type ChatMessage = { role: 'user' | 'assistant'; content: string }

export async function* streamLessonChat(
  lessonId: string,
  persona: string,
  messages: ChatMessage[],
): AsyncGenerator<{ type: string; text?: string; message?: string }> {
  const res = await fetch(`${API_URL}/lesson/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lesson_id: lessonId, persona, messages }),
  })

  if (!res.ok || !res.body) throw new Error(`Chat error: ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw) yield JSON.parse(raw)
      }
    }
  }
}
