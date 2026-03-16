import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { sendMessage, type OnboardingMessage } from '../api/onboarding'

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<OnboardingMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showContinueButton, setShowContinueButton] = useState(false)

  async function handleChatSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg: OnboardingMessage = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await sendMessage(nextMessages, {})
      setMessages((m) => [...m, { role: 'assistant', content: res.message }])
      if (res.done) {
        setShowContinueButton(true)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (messages.length > 0 || loading) return
    let cancelled = false
    setLoading(true)
    sendMessage([], {}).then((res) => {
      if (!cancelled) {
        setMessages([{ role: 'assistant', content: res.message }])
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-stone-50 via-amber-50/30 to-stone-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 font-sans text-slate-800 dark:text-slate-100 antialiased">
      <header className="flex items-center justify-between px-8 py-5 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b-2 border-emerald-200/60 dark:border-slate-700/50 shrink-0">
        <Link to="/login" className="flex items-center gap-4">
          <div className="size-12 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary ring-1 ring-primary/20 shrink-0">
            <span className="material-symbols-outlined text-3xl font-light">
              rocket_launch
            </span>
          </div>
          <h2 className="text-slate-900 dark:text-white text-base font-bold leading-tight font-logo tracking-normal">
            Generative Learning Platform
          </h2>
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-2xl flex flex-col h-[70vh] min-h-[400px]">
          {messages.length === 0 && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center">
              <p className="text-slate-500 dark:text-slate-400">
                Preparing your chat...
              </p>
            </div>
          )}
          {(messages.length > 0 || loading) && (
            <>
              <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                        m.role === 'assistant'
                          ? 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100'
                          : 'bg-primary text-white'
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-100 dark:bg-slate-800 px-4 py-3 rounded-2xl text-slate-500">
                      ...
                    </div>
                  </div>
                )}
              </div>
              {showContinueButton ? (
                <div className="mt-4 shrink-0">
                  <button
                    type="button"
                    onClick={() => navigate('/roadmap', { replace: true })}
                    className="w-full bg-gradient-to-r from-primary to-primary-light text-white font-bold py-4 px-6 rounded-2xl shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all"
                  >
                    Continue to GLP
                  </button>
                </div>
              ) : (
                <form onSubmit={handleChatSubmit} className="mt-4 shrink-0">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Tell me about yourself..."
                      disabled={loading}
                      className="flex-1 px-4 py-3 rounded-2xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 focus:border-primary focus:outline-none disabled:opacity-60"
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || loading}
                      className="bg-primary text-white font-bold px-6 py-3 rounded-2xl hover:bg-primary-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Send
                    </button>
                  </div>
                </form>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
