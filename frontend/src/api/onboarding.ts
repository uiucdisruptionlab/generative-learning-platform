export type OnboardingMessage = {
  role: 'user' | 'assistant'
  content: string
}

export type OnboardingProfile = {
  name: string | null
  major: string | null
  minor: string | null
  academic_level: string | null
  career_goals: string | null
  career_clarity: string | null
  subject_confidence: string | null
  learning_style_summary: string | null
  weekly_hours: number | null
  preferred_formats: string[] | null
  interests: string[] | null
  notes: string | null
}

export type ChatResponse = {
  message: string
  profile: OnboardingProfile
  done: boolean
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type StreamEvent =
  | { type: 'chunk'; text: string }
  | { type: 'result'; message: string; profile: OnboardingProfile; done: boolean }
  | { type: 'error'; message: string }

export function emptyProfile(): OnboardingProfile {
  return {
    name: null,
    major: null,
    minor: null,
    academic_level: null,
    career_goals: null,
    career_clarity: null,
    subject_confidence: null,
    learning_style_summary: null,
    weekly_hours: null,
    preferred_formats: null,
    interests: null,
    notes: null,
  }
}

export async function* streamMessage(
  messages: OnboardingMessage[],
  profile: OnboardingProfile,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, profile }),
  })

  if (!res.ok || !res.body) {
    const detail = await res.text()
    throw new Error(`Backend error ${res.status}: ${detail}`)
  }

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
        if (raw) yield JSON.parse(raw) as StreamEvent
      }
    }
  }
}
