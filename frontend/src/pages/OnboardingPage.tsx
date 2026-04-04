import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { streamMessage, emptyProfile, type OnboardingMessage, type OnboardingProfile } from '../api/onboarding'
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard'

function titleCase(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function toDisplayProfile(p: OnboardingProfile): LearnerProfile {
  const now = new Date().toISOString()

  // Build llm_profile with human-readable keys and formatted values.
  // "Learning Style" is stored first so LearnerProfileCard can render it full-width.
  const llm: Record<string, string> = {}
  if (p.learning_style_summary) llm['Learning Style'] = p.learning_style_summary
  if (p.career_clarity)    llm['Career Clarity']    = titleCase(p.career_clarity)
  if (p.subject_confidence) llm['Prior Experience']  = titleCase(p.subject_confidence)
  if (p.minor)              llm['Minor']             = p.minor
  if (p.notes)              llm['Notes']             = p.notes

  return {
    id: `onboarding-${Date.now()}`,
    name: p.name ?? 'Learner',
    major_or_field: p.major ?? 'Undeclared',
    learning_goals: p.career_goals ? [p.career_goals] : [],
    interests: p.interests ?? [],
    academic_level: p.academic_level ?? 'Student',
    weekly_hours: p.weekly_hours ?? 0,
    preferred_formats: p.preferred_formats ?? [],
    llm_profile: Object.keys(llm).length > 0 ? llm : null,
    created_at: now,
    updated_at: now,
  }
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<OnboardingMessage[]>([])
  const [profile, setProfile] = useState<OnboardingProfile>(emptyProfile())
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [doneProfile, setDoneProfile] = useState<OnboardingProfile | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Fetch opening greeting on mount via streaming
  useEffect(() => {
    if (messages.length > 0 || loading) return
    let cancelled = false
    setLoading(true)

    ;(async () => {
      try {
        // seed an empty assistant bubble
        setMessages([{ role: 'assistant', content: '' }])
        for await (const event of streamMessage([], emptyProfile())) {
          if (cancelled) break
          if (event.type === 'chunk') {
            setMessages((m) => {
              const updated = [...m]
              updated[updated.length - 1] = { role: 'assistant', content: updated[updated.length - 1].content + event.text }
              return updated
            })
          } else if (event.type === 'result') {
            setMessages([{ role: 'assistant', content: event.message }])
          }
        }
      } catch (err) {
        if (!cancelled) setError(String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading && !doneProfile) inputRef.current?.focus()
  }, [loading, doneProfile, messages])

  async function handleChatSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg: OnboardingMessage = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      // Seed an empty assistant bubble that we'll fill as chunks arrive
      setMessages((m) => [...m, { role: 'assistant', content: '' }])

      for await (const event of streamMessage(nextMessages, profile)) {
        if (event.type === 'chunk') {
          setMessages((m) => {
            const updated = [...m]
            updated[updated.length - 1] = {
              role: 'assistant',
              content: updated[updated.length - 1].content + event.text,
            }
            return updated
          })
        } else if (event.type === 'result') {
          // Snap to the clean final text, then update profile state
          setMessages((m) => {
            const updated = [...m]
            updated[updated.length - 1] = { role: 'assistant', content: event.message }
            return updated
          })
          setProfile(event.profile)
          if (event.done) setDoneProfile(event.profile)
        } else if (event.type === 'error') {
          setError(event.message)
        }
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  function handleContinue() {
    if (doneProfile) {
      const display = toDisplayProfile(doneProfile)
      localStorage.setItem('glp_learner_profile', JSON.stringify(display))
    }
    navigate('/roadmap', { replace: true })
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-stone-50 via-amber-50/30 to-stone-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 font-sans text-slate-800 dark:text-slate-100 antialiased">
      <header className="flex items-center justify-between px-8 py-5 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b-2 border-emerald-200/60 dark:border-slate-700/50 shrink-0">
        <Link to="/login" className="flex items-center gap-4">
          <div className="size-12 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary ring-1 ring-primary/20 shrink-0">
            <span className="material-symbols-outlined text-3xl font-light">rocket_launch</span>
          </div>
          <h2 className="text-slate-900 dark:text-white text-base font-bold leading-tight font-logo tracking-normal">
            Generative Learning Platform
          </h2>
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-6">
        {doneProfile ? (
          /* ── Profile reveal ── */
          <div className="w-full max-w-4xl flex flex-col gap-8">
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-bold text-primary border border-primary/20 mb-2">
                <span className="material-symbols-outlined text-base">check_circle</span>
                Onboarding complete
              </div>
              <h1 className="text-3xl font-extrabold font-display text-slate-900 dark:text-white">
                Here's what I learned about you
              </h1>
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                This profile will personalise your learning path.
              </p>
            </div>

            <LearnerProfileCard profile={toDisplayProfile(doneProfile)} />

            <button
              type="button"
              onClick={handleContinue}
              className="w-full bg-primary hover:bg-emerald-700 text-white font-bold py-4 px-6 rounded-2xl shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 transition-all duration-300 transform hover:scale-[1.02]"
            >
              Continue to GLP →
            </button>
          </div>
        ) : (
          /* ── Chat ── */
          <div className="w-full max-w-2xl flex flex-col h-[70vh] min-h-[400px]">
            {messages.length === 0 && !loading && !error && (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-slate-500 dark:text-slate-400">Preparing your chat…</p>
              </div>
            )}

            {error && (
              <div className="mb-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                <span className="font-bold">Connection error: </span>{error}
                <span className="ml-1 text-xs opacity-70">(Is the backend running on port 8000?)</span>
              </div>
            )}

            {(messages.length > 0 || loading) && (
              <>
                <div className="flex-1 overflow-y-auto scrollbar-none space-y-4 pb-4">
                  {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
                  {loading && messages[messages.length - 1]?.role === 'user' && (
                    <div className="flex justify-start">
                      <div className="bg-slate-100 dark:bg-slate-800 px-4 py-3 rounded-2xl text-slate-500">…</div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleChatSubmit} className="mt-4 shrink-0">
                  <div className="flex gap-3">
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Tell me about yourself…"
                      disabled={loading}
                      autoFocus
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
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
