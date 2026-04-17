import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { usePersona } from '../contexts/PersonaContext'
import { fetchLesson, scoreLessonResponse, streamLessonChat, type LessonContent, type LessonQuestion, type ChatMessage, type LessonScoreResponse } from '../api/lesson'

// ---------- Video card ----------

function VideoCard({ video }: { video: LessonContent['videos'][0] }) {
  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-3 hover:border-primary/50 transition-colors"
    >
      <img src={video.thumbnail} alt={video.title} className="w-24 h-16 rounded-lg object-cover flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-900 dark:text-white line-clamp-2">{video.title}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{video.channel}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 line-clamp-1">{video.reason}</p>
      </div>
    </a>
  )
}

// ---------- Question card ----------

type QuestionAnswer = {
  question: string
  learnerAnswer: string
  correctAnswer: string
  isCorrect: boolean
}

function QuestionCard({
  question,
  index,
  onAnswered,
}: {
  question: LessonQuestion
  index: number
  onAnswered: (index: number, answer: QuestionAnswer | null) => void
}) {
  const [selected, setSelected] = useState<string | null>(null)
  const [fillValue, setFillValue] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const currentAnswer = question.type === 'multiple_choice' ? selected ?? '' : fillValue.trim()
  const answerIsCorrect = (
    question.type === 'multiple_choice'
      ? selected === question.answer
      : fillValue.trim().toLowerCase() === question.answer.trim().toLowerCase()
  )
  const isCorrect = submitted && answerIsCorrect

  const handleSubmit = () => {
    if (question.type === 'multiple_choice' && !selected) return
    if (question.type === 'fill_in_the_blank' && !fillValue.trim()) return
    setSubmitted(true)
    onAnswered(index, {
      question: question.question,
      learnerAnswer: currentAnswer,
      correctAnswer: question.answer,
      isCorrect: answerIsCorrect,
    })
  }

  const handleRetry = () => {
    setSelected(null)
    setFillValue('')
    setSubmitted(false)
    onAnswered(index, null)
  }

  return (
    <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-slate-200 dark:border-slate-700 shadow-soft">
      <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
        Question {index + 1} · {question.type === 'multiple_choice' ? 'Multiple Choice' : 'Fill in the Blank'}
      </p>
      <p className="text-slate-900 dark:text-white font-medium mb-4">{question.question}</p>

      {question.type === 'multiple_choice' && question.options && (
        <div className="space-y-2 mb-4">
          {question.options.map((opt) => {
            const isSelected = selected === opt
            const isAnswer = submitted && opt === question.answer
            const isWrong = submitted && isSelected && opt !== question.answer
            return (
              <button key={opt} type="button" disabled={submitted} onClick={() => setSelected(opt)}
                className={`w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition-all ${
                  isAnswer ? 'border-primary bg-emerald-50 dark:bg-emerald-900/20 text-primary font-semibold'
                  : isWrong ? 'border-red-400 bg-red-50 dark:bg-red-900/20 text-red-600'
                  : isSelected ? 'border-primary bg-primary/5 text-slate-900 dark:text-white'
                  : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-primary/40'
                }`}
              >{opt}</button>
            )
          })}
        </div>
      )}

      {question.type === 'fill_in_the_blank' && (
        <input type="text" value={fillValue} disabled={submitted}
          onChange={(e) => setFillValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
          placeholder="Type your answer…"
          className={`w-full px-4 py-3 rounded-xl border-2 text-sm mb-4 focus:outline-none transition-colors ${
            submitted
              ? isCorrect ? 'border-primary bg-emerald-50 dark:bg-emerald-900/20 text-primary'
                : 'border-red-400 bg-red-50 dark:bg-red-900/20 text-red-600'
              : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 focus:border-primary'
          }`}
        />
      )}

      {submitted ? (
        <div className={`rounded-xl p-3 mb-3 text-sm ${isCorrect ? 'bg-emerald-50 dark:bg-emerald-900/20 text-primary' : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'}`}>
          <p className="font-semibold mb-1">{isCorrect ? 'Correct!' : `Incorrect — the answer is: ${question.answer}`}</p>
          <p className="text-xs opacity-80">{question.explanation}</p>
        </div>
      ) : (
        <button type="button" onClick={handleSubmit}
          className="px-5 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary-light transition-colors">
          Submit
        </button>
      )}

      {submitted && (
        <button type="button" onClick={handleRetry}
          className="mt-2 px-4 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs text-slate-500 hover:border-primary/40 transition-colors">
          Try again
        </button>
      )}
    </div>
  )
}

// ---------- Chatbot ----------

function LessonChatbot({ lessonId, persona }: { lessonId: string; persona: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming) return

    const userMessage: ChatMessage = { role: 'user', content: text }
    const nextMessages = [...messages, userMessage]
    setMessages(nextMessages)
    setInput('')
    setStreaming(true)
    let assistantText = ''
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    try {
      for await (const event of streamLessonChat(lessonId, persona, nextMessages)) {
        if (event.type === 'chunk' && event.text) {
          assistantText += event.text
          setMessages((prev) => [...prev.slice(0, -1), { role: 'assistant', content: assistantText }])
        }
      }
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="border-t-2 border-slate-200 dark:border-slate-700 pt-6 mt-2">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">smart_toy</span>
        Ask your lesson assistant
      </h3>
      {messages.length > 0 && (
        <div className="space-y-3 mb-4 max-h-80 overflow-y-auto">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-primary text-white rounded-br-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-sm'
              }`}>
                {m.content || <span className="opacity-50 animate-pulse">…</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
      <div className="flex gap-2">
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSend() }}
          placeholder="Ask anything about this lesson…" disabled={streaming}
          className="flex-1 px-4 py-2.5 rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 focus:border-primary focus:outline-none text-sm disabled:opacity-50"
        />
        <button type="button" onClick={handleSend} disabled={streaming || !input.trim()}
          className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary-light disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          {streaming ? '…' : 'Ask'}
        </button>
      </div>
    </div>
  )
}

// ---------- Main page ----------

export default function LessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>()
  const [searchParams] = useSearchParams()
  const { currentPersona } = usePersona()
  const courseOverride = searchParams.get('course') ?? undefined

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [lesson, setLesson] = useState<LessonContent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<number, QuestionAnswer>>({})
  const [scoring, setScoring] = useState(false)
  const [scoreResult, setScoreResult] = useState<LessonScoreResponse | null>(null)
  const [scoreError, setScoreError] = useState<string | null>(null)

  const persona = currentPersona === 'demo' ? 'charles' : currentPersona

  useEffect(() => {
    if (!lessonId) return
    setLoading(true)
    setAnswers({})
    setScoreResult(null)
    setScoreError(null)
    fetchLesson(lessonId, persona, courseOverride)
      .then((data) => { setLesson(data); setError(null) })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [lessonId, persona, courseOverride])

  const answeredCount = Object.keys(answers).length
  const allQuestionsAnswered = Boolean(lesson?.questions.length) && answeredCount === lesson?.questions.length

  const handleAnswered = (index: number, answer: QuestionAnswer | null) => {
    setScoreResult(null)
    setScoreError(null)
    setAnswers((prev) => {
      const next = { ...prev }
      if (answer) next[index] = answer
      else delete next[index]
      return next
    })
  }

  const handleRecordProgress = async () => {
    if (!lesson || !lessonId || !allQuestionsAnswered || scoring) return

    const orderedAnswers = lesson.questions.map((_, index) => answers[index]).filter(Boolean)
    const response = orderedAnswers.map((answer, index) => (
      `Question ${index + 1}: ${answer.question}\nLearner answer: ${answer.learnerAnswer}\nCorrect answer: ${answer.correctAnswer}\nResult: ${answer.isCorrect ? 'correct' : 'incorrect'}`
    )).join('\n\n')

    const referenceAnswer = lesson.questions.map((question, index) => (
      `Question ${index + 1}: ${question.answer}. ${question.explanation}`
    )).join('\n')

    setScoring(true)
    setScoreError(null)
    try {
      const result = await scoreLessonResponse({
        lesson_id: lessonId,
        persona,
        course: courseOverride,
        response,
        question: 'Score the learner across all generated lesson knowledge checks.',
        reference_answer: referenceAnswer,
        metadata: {
          lesson_title: lesson.title,
          question_count: lesson.questions.length,
          correct_count: orderedAnswers.filter((answer) => answer.isCorrect).length,
          concepts: lesson.concepts ?? [],
        },
      })
      setScoreResult(result)
    } catch (err) {
      setScoreError(String(err))
    } finally {
      setScoring(false)
    }
  }

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title={lesson?.title ?? 'Loading lesson…'}
      description={lesson?.overview ?? ''}
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-32 min-w-0">
        {error && (
          <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            Failed to load lesson: {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-24 text-gray-400 dark:text-gray-500">
            <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            <p className="text-sm">Generating your personalized lesson…</p>
          </div>
        ) : lesson && (
          <div className="space-y-8">

            {/* Overview */}
            <div className="rounded-2xl bg-primary/5 dark:bg-primary/10 border-2 border-primary/20 p-5">
              <p className="text-slate-700 dark:text-slate-300 leading-relaxed">{lesson.overview}</p>
            </div>

            {/* Steps — all rendered as a scroll */}
            {lesson.steps.map((step) => {
              const borderColor = step.type === 'example'
                ? 'border-amber-200/80 dark:border-amber-800/40'
                : step.type === 'summary'
                ? 'border-primary/30 dark:border-primary/20'
                : 'border-slate-200 dark:border-slate-700'
              const badge = step.type === 'example'
                ? { label: 'Example', icon: 'lightbulb', color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20' }
                : step.type === 'summary'
                ? { label: 'Summary', icon: 'summarize', color: 'text-primary bg-emerald-50 dark:bg-emerald-900/20' }
                : { label: 'Concept', icon: 'school', color: 'text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800' }
              return (
                <div key={step.step_number} className={`rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 ${borderColor} shadow-soft`}>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mb-3 ${badge.color}`}>
                    <span className="material-symbols-outlined text-sm">{badge.icon}</span>
                    {badge.label}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">{step.title}</h3>
                  <p className="text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">{step.content}</p>
                </div>
              )
            })}

            {/* Videos */}
            {lesson.videos.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Related Videos</h3>
                {lesson.videos.map((v, i) => <VideoCard key={i} video={v} />)}
              </div>
            )}

            {/* Questions */}
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Check Your Understanding</h3>
              {lesson.questions.map((q, i) => (
                <QuestionCard key={i} question={q} index={i} onAnswered={handleAnswered} />
              ))}
              <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 border-2 border-slate-200 dark:border-slate-700 p-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">Lesson progress</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      {answeredCount} of {lesson.questions.length} checks completed
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRecordProgress}
                    disabled={!allQuestionsAnswered || scoring || Boolean(scoreResult)}
                    className="px-5 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-light disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {scoring ? 'Recording…' : scoreResult ? 'Recorded' : 'Record progress'}
                  </button>
                </div>
                {scoreResult && (
                  <div className="mt-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-4 py-3 text-sm text-primary">
                    <p className="font-semibold">Score: {scoreResult.score}/5 · {scoreResult.passed ? 'Passed' : 'Needs review'}</p>
                    {scoreResult.explanation && <p className="mt-1 text-xs opacity-80">{scoreResult.explanation}</p>}
                  </div>
                )}
                {scoreError && (
                  <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                    Failed to record progress: {scoreError}
                  </div>
                )}
              </div>
            </div>

            {/* Chatbot */}
            <LessonChatbot lessonId={lessonId!} persona={persona} />
          </div>
        )}
      </div>
    </AppLayout>
  )
}
