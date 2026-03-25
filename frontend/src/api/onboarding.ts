export type OnboardingMessage = {
  role: 'user' | 'assistant'
  content: string
}

export type OnboardingProfile = {
  name: string | null
  major: string | null
  minor: string | null
  career_goals: string | null
  career_clarity: string | null
  subject_confidence: string | null
  learning_style_summary: string | null
  interests: string[] | null
  notes: string | null
}

export type ChatResponse = {
  message: string
  profile: OnboardingProfile
  done: boolean
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function emptyProfile(): OnboardingProfile {
  return {
    name: null,
    major: null,
    minor: null,
    career_goals: null,
    career_clarity: null,
    subject_confidence: null,
    learning_style_summary: null,
    interests: null,
    notes: null,
  }
}

export async function sendMessage(
  messages: OnboardingMessage[],
  profile: OnboardingProfile,
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, profile }),
  })

  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`Backend error ${res.status}: ${detail}`)
  }

  return res.json() as Promise<ChatResponse>
}
