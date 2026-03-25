export interface OnboardingMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface OnboardingResponse {
  message: string;  // Maps to backend 'reply'
  done: boolean;     // Maps to backend 'is_onboarding_complete'
  updates?: Record<string, any>;
}

export async function sendMessage(
  messages: OnboardingMessage[],
  _quizAnswers: any 
): Promise<OnboardingResponse> {
  try {
    // Bedrock fails on empty strings, so we ensure a default "Hello"
    const lastContent = messages.length > 0 ? messages[messages.length - 1].content.trim() : "";
    const messageToSend = lastContent || "Hello";

    const response = await fetch("http://127.0.0.1:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        message: messageToSend,
        history: messages.slice(0, -1),
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Server error");
    }

    const data = await response.json();

    return {
      message: data.reply,
      done: data.is_onboarding_complete,
      updates: data.updates
    };
  } catch (error) {
    console.error("Connection Error:", error);
    return {
      message: "I'm having a bit of trouble connecting to my brain. Is the backend running?",
      done: false
    };
  }
}