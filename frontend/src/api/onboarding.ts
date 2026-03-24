export type OnboardingMessage = {
  role: 'user' | 'assistant'
  content: string
}

export type QuizAnswers = Record<string, string>

export type OnboardingResponse = {
  message: string
  options?: string[]
  done?: boolean
}

/**
 * Mock onboarding chat API. Simulates multi-turn conversation
 * to collect name, major, career goals, and prior knowledge.
 * Returns done: true after a few exchanges.
 */
export async function sendMessage(
  messages: OnboardingMessage[],
  quizAnswers: QuizAnswers
): Promise<OnboardingResponse> {
  // Simulate network delay
  await new Promise((r) => setTimeout(r, 600))

  const messageCount = messages.length

  // Simple mock: respond based on turn count and user input
  if (messageCount === 0) {
    return {
      message: "Hello! What's your name?",
    }
  }
  if (messageCount === 2) {
    const name = messages[messages.length - 1]?.content || 'there'
    return {
      message: `Nice to meet you, ${name}! What's your major or area of study?`,
    }
  }
  if (messageCount === 4) {
    return {
      message:
        "Thanks! What are your main career goals? What kind of work do you see yourself doing?",
    }
  }
  if (messageCount === 6) {
    return {
      message:
        "One more thing: what's your prior experience with this subject? Are you new to it or do you have some background?",
    }
  }
  // messageCount >= 8: user just answered prior experience
  return {
    message: "Thanks, that's all I needed!",
    done: true,
  }
}
