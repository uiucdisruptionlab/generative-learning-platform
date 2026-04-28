import { MouseEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import type { HomeRoadmapConcept, HomeRoadmapOutcome } from '../data/homeRoadmapPreview'
import { usePersona } from '../contexts/PersonaContext'
import {
  fetchHomeData,
  startSession,
  type DueSrsRecord,
  type GeneratedRoadmap,
  type GeneratedRoadmapConcept,
  type GeneratedRoadmapLesson,
  type StudentProfile,
} from '../api/home'

type RecommendationCard = {
  icon: string
  badge: string
  badgeColor: string
  iconColor: string
  borderColor: string
  title: string
  meta: string
}

type HomeData = Awaited<ReturnType<typeof fetchHomeData>>

function conceptTitle(nodeId: string, concepts: GeneratedRoadmapConcept[] = []): string {
  const found = concepts.find((concept) => concept.id === nodeId || concept.name === nodeId)
  return found?.name || found?.id || nodeId
}

function studentSubtitle(student: StudentProfile): string {
  return (
    student.llm_profile?.notes ||
    student.learning_goals?.target_course ||
    student.learning_goals?.primary_focus ||
    student.major_or_field ||
    ''
  )
}

function formatConfig(format: string): Omit<RecommendationCard, 'title'> {
  const lower = format.toLowerCase()
  if (lower.includes('video')) {
    return {
      icon: 'play_circle',
      badge: 'Video Lesson',
      badgeColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400',
      iconColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 group-hover:bg-red-600',
      borderColor: 'border-red-200/70 dark:border-red-700/40 hover:border-red-500/60',
      meta: 'Personalized video',
    }
  }
  if (lower.includes('hands') || lower.includes('practice') || lower.includes('problem') || lower.includes('exercise')) {
    return {
      icon: 'code',
      badge: 'Hands-On',
      badgeColor: 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
      iconColor: 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 group-hover:bg-indigo-600',
      borderColor: 'border-indigo-200/70 dark:border-indigo-700/40 hover:border-indigo-500/60',
      meta: 'Practice activity',
    }
  }
  if (lower.includes('flash')) {
    return {
      icon: 'style',
      badge: 'Flashcards',
      badgeColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary',
      iconColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary group-hover:bg-primary',
      borderColor: 'border-emerald-200/70 dark:border-emerald-700/40 hover:border-primary/60',
      meta: 'Review cards',
    }
  }
  if (lower.includes('quiz') || lower.includes('question')) {
    return {
      icon: 'quiz',
      badge: 'Quick Quiz',
      badgeColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent',
      iconColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent group-hover:bg-accent',
      borderColor: 'border-orange-200/70 dark:border-orange-700/40 hover:border-accent/60',
      meta: 'Knowledge check',
    }
  }
  if (lower.includes('ai') || lower.includes('discussion')) {
    return {
      icon: 'forum',
      badge: 'AI Discussion',
      badgeColor: 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
      iconColor: 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 group-hover:bg-purple-600',
      borderColor: 'border-purple-200/70 dark:border-purple-700/40 hover:border-purple-500/60',
      meta: 'Interactive chat',
    }
  }
  return {
    icon: 'auto_stories',
    badge: format || 'Reading',
    badgeColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary',
    iconColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary group-hover:bg-secondary',
    borderColor: 'border-amber-200/70 dark:border-amber-700/40 hover:border-secondary/60',
    meta: 'Study material',
  }
}

function makeRecommendations(student: StudentProfile, activeConcept: string): RecommendationCard[] {
  const formats = student.preferred_formats?.length ? student.preferred_formats : []
  return formats.slice(0, 3).map((format) => {
    const config = formatConfig(format)
    return {
      ...config,
      title: `${config.badge}: ${activeConcept}`,
    }
  })
}

function lessonStateToStatus(state: GeneratedRoadmapLesson['state']): HomeRoadmapOutcome['status'] {
  if (state === 'completed') return 'completed'
  if (state === 'active') return 'current'
  return 'upcoming'
}

function toConcept(c: GeneratedRoadmapConcept): HomeRoadmapConcept {
  return {
    id: String(c.id ?? c.name ?? ''),
    name: c.name ?? c.id ?? '',
    description: c.description,
    status: lessonStateToStatus(c.state ?? 'locked'),
  }
}

function makeLessonOutcomes(roadmap: GeneratedRoadmap | undefined): HomeRoadmapOutcome[] {
  const lessons = roadmap?.lessons ?? []
  if (!lessons.length) return []
  const activeIndex = Math.max(0, lessons.findIndex((lesson) => lesson.state === 'active'))
  const start = Math.max(0, activeIndex - 1)
  const end = Math.min(lessons.length, activeIndex + 2)
  return lessons.slice(start, end).map((lesson) => {
    const conceptCount = lesson.concepts?.length ?? 0
    return {
      id: lesson.lesson_id,
      title: lesson.title,
      status: lessonStateToStatus(lesson.state),
      subtext:
        lesson.state === 'active'
          ? lesson.summary?.trim() || 'Based on your progress, this is the right place to start.'
          : conceptCount
            ? `${conceptCount} concept${conceptCount === 1 ? '' : 's'}`
            : undefined,
      concepts: (lesson.concepts ?? []).map(toConcept),
    }
  })
}

function formatMonth(date: Date): string {
  return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}

function formatDueText(value?: string): string {
  if (!value) return 'Review scheduled'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Review scheduled'
  return date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
}

export default function HomePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { persona, studentId } = usePersona()
  const [homeData, setHomeData] = useState<HomeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchHomeData(studentId)
      .then((data) => {
        if (!cancelled) setHomeData(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  const currentIndex = homeData?.roadmapPosition.current_index ?? 0
  const nodeIds = homeData?.roadmap.node_ids ?? []
  const lessons = homeData?.roadmap.lessons ?? []
  const activeLesson = useMemo(() => lessons.find((lesson) => lesson.state === 'active'), [lessons])
  const activeNodeId =
    activeLesson?.concepts.find((c) => c.state === 'active')?.id ??
    nodeIds[Math.min(Math.max(currentIndex, 0), Math.max(nodeIds.length - 1, 0))] ??
    ''
  const activeConcept = activeLesson?.title || (activeNodeId ? conceptTitle(activeNodeId, homeData?.roadmap.concepts) : '')
  const progress = nodeIds.length ? Math.round((currentIndex / nodeIds.length) * 100) : 0
  const subtitle = homeData ? studentSubtitle(homeData.student) : ''
  const homeRoadmapPath = persona ? persona.primaryRoadmapPath : '/roadmap'
  const roadmapOutcomes = useMemo(() => makeLessonOutcomes(homeData?.roadmap), [homeData?.roadmap])
  const recommendations = homeData ? makeRecommendations(homeData.student, activeConcept) : []
  const dueReviews = useMemo(() => {
    const now = Date.now()
    const nextWeek = now + 7 * 24 * 60 * 60 * 1000
    return (homeData?.srsDue.due ?? []).filter((record) => {
      if (!record.next_review_at) return false
      const time = new Date(record.next_review_at).getTime()
      return Number.isFinite(time) && time >= now && time <= nextWeek
    })
  }, [homeData?.srsDue.due])
  const firstDueDate = dueReviews[0]?.next_review_at ? new Date(dueReviews[0].next_review_at) : null
  const handleStartHere = async (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    try {
      const session = await startSession(studentId)
      navigate(`/lesson?session_id=${encodeURIComponent(session.session_id)}`)
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Home"
      description="Your personalized learning hub and AI-enhanced recommendations."
      sidebarProfileOverride={
        homeData
          ? {
              displayName: homeData.student.name,
              studentId: homeData.student.id,
            }
          : undefined
      }
    >
      <div className="max-w-[1200px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12 space-y-8">
        {loading && (
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">Loading your learning hub...</p>
          </section>
        )}

        {error && !loading && (
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-red-200/80 dark:border-red-800/40 shadow-soft">
            <p className="text-sm font-semibold text-red-700 dark:text-red-300">{error}</p>
          </section>
        )}

        {homeData && !loading && !error && (
          <>
        <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft bg-gradient-to-br from-white via-amber-50/20 to-white dark:from-slate-900 dark:via-slate-900/50 dark:to-slate-900">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white font-display">
                Welcome back, {homeData.student.name}.
              </h1>
              {subtitle && (
                <p className="text-sm text-slate-600 dark:text-slate-300 font-semibold">
                  {subtitle}
                </p>
              )}
              <p className="text-slate-500 dark:text-slate-400 font-medium">
                Your personalized learning path is <span className="text-primary font-bold">{progress}% complete</span>.
              </p>
            </div>
            <div className="flex gap-3">
              <button className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light transition-all shadow-md shadow-primary/20">
                Resume Learning
              </button>
              <button className="rounded-xl border-2 border-primary/30 px-5 py-2.5 text-sm font-bold text-primary hover:bg-primary/10 dark:hover:bg-primary/20 transition-colors">
                View Full Path
              </button>
            </div>
          </div>
          <div className="mt-8 space-y-3">
            <div className="flex justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Core Fundamentals</span>
              <span>Advanced Specialization</span>
            </div>
            <div className="relative h-4 w-full overflow-hidden rounded-full bg-stone-200/80 dark:bg-slate-800">
              <div
                className="absolute h-full rounded-full bg-gradient-to-r from-primary to-primary-light shadow-lg shadow-primary/30"
                style={{ width: `${progress}%` }}
              />
              <div className="absolute inset-0 flex">
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4" />
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-5">
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
                <span className="material-symbols-outlined text-primary shrink-0">route</span>
                <span className="break-words">{subtitle || activeConcept || 'Your Roadmap'}</span>
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {lessons.length} lesson{lessons.length === 1 ? '' : 's'} · Personalized for {homeData.student.name}
              </p>
            </div>
          </div>
          <LearningRoadmap
            key={homeRoadmapPath}
            compact
            showViewFullLink
            scrollable
            outcomes={roadmapOutcomes}
            startHereTo={activeLesson ? `/lesson?lesson_id=${encodeURIComponent(activeLesson.lesson_id)}` : homeRoadmapPath}
            viewFullTo={homeRoadmapPath}
            onStartHere={handleStartHere}
            buildTranscriptHref={(concept) =>
              `/lesson/transcript?student_id=${encodeURIComponent(studentId)}&concept_id=${encodeURIComponent(concept.id)}`
            }
          />
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 min-w-0">
          <div className="xl:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 font-display">
                <span className="material-symbols-outlined text-primary">auto_awesome</span>
                Top Recommendations for You
              </h2>
              <button className="text-sm font-semibold text-primary hover:underline">Customize feed</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recommendations.map((rec, index) => (
                <div
                  key={index}
                  className={`group flex flex-col rounded-2xl bg-white/95 dark:bg-slate-900/95 border-2 p-4 shadow-soft transition-all duration-300 hover:shadow-xl ${rec.borderColor}`}
                >
                  <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg ${rec.iconColor} group-hover:text-white transition-colors`}>
                    <span className="material-symbols-outlined">{rec.icon}</span>
                  </div>
                  <span className={`mb-2 inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${rec.badgeColor}`}>
                    {rec.badge}
                  </span>
                  <h3 className="mb-4 text-sm font-bold text-stone-900 dark:text-white leading-snug font-display">
                    {rec.title}
                  </h3>
                  <div className="mt-auto flex items-center justify-between">
                    <span className="text-xs text-stone-400">{rec.meta}</span>
                    <span className="material-symbols-outlined text-stone-300 group-hover:text-primary">arrow_forward</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {dueReviews.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 font-display">
              <span className="material-symbols-outlined text-primary">event_note</span>
              Upcoming Milestones
            </h2>
            <div className="rounded-2xl border border-primary/20 dark:border-primary/30 bg-white dark:bg-slate-900 p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  {firstDueDate ? formatMonth(firstDueDate) : ''}
                </span>
                <div className="flex gap-2">
                  <span className="material-symbols-outlined text-lg text-slate-400 cursor-pointer">chevron_left</span>
                  <span className="material-symbols-outlined text-lg text-slate-400 cursor-pointer">chevron_right</span>
                </div>
              </div>
              <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-bold text-slate-400 uppercase mb-2">
                <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
              </div>
              <div className="grid grid-cols-7 gap-1 text-center">
                {Array.from({ length: 14 }, (_, index) => {
                  const base = firstDueDate ? new Date(firstDueDate) : new Date()
                  base.setDate(base.getDate() - 6 + index)
                  const hasReview = dueReviews.some((record) => {
                    if (!record.next_review_at) return false
                    const reviewDate = new Date(record.next_review_at)
                    return reviewDate.toDateString() === base.toDateString()
                  })
                  return (
                    <div
                      key={base.toISOString()}
                      className={`p-1 text-xs ${hasReview ? 'font-bold text-primary ring-1 ring-primary rounded-md' : 'text-slate-800 dark:text-slate-300'}`}
                    >
                      {base.getDate()}
                    </div>
                  )
                })}
              </div>
            </div>
            <div className="space-y-4">
              {dueReviews.slice(0, 3).map((record: DueSrsRecord, index) => {
                const nodeId = String(record.node_id || record.concept_id || '')
                const border = index === 0
                  ? 'border-red-400 border-red-100 dark:border-red-900/40'
                  : index === 1
                    ? 'border-primary border-emerald-100 dark:border-emerald-900/40'
                    : 'border-slate-300 border-slate-200 dark:border-slate-700'
                const labelColor = index === 0 ? 'text-red-500' : index === 1 ? 'text-primary' : 'text-slate-400'
                return (
                  <div key={`${nodeId}-${record.next_review_at}`} className={`flex gap-4 rounded-xl border-l-4 bg-white dark:bg-slate-900 p-4 shadow-sm border-2 ${border}`}>
                    <div className="flex-1 space-y-1">
                      <p className={`text-[10px] font-bold uppercase tracking-wider ${labelColor}`}>
                        {index === 0 ? 'High Priority' : index === 1 ? 'Assessment' : 'Study Reminder'}
                      </p>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">
                        Review: {conceptTitle(nodeId, homeData.roadmap.concepts)}
                      </h4>
                      <p className="text-xs text-slate-500">{formatDueText(record.next_review_at)}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          )}
        </div>
        </>
        )}
      </div>
    </AppLayout>
  )
}
