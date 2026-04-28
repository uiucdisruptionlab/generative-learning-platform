import { MouseEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import type { HomeRoadmapConcept, HomeRoadmapOutcome } from '../data/homeRoadmapPreview'
import { usePersona } from '../contexts/PersonaContext'
import {
  fetchStudentRoadmapData,
  startSession,
  type GeneratedRoadmap,
  type GeneratedRoadmapConcept,
  type GeneratedRoadmapLesson,
  type RoadmapState,
} from '../api/home'

type RoadmapData = Awaited<ReturnType<typeof fetchStudentRoadmapData>>

function stateToStatus(state: RoadmapState | undefined): HomeRoadmapOutcome['status'] {
  if (state === 'completed') return 'completed'
  if (state === 'active') return 'current'
  return 'upcoming'
}

function lessonSubtext(lesson: GeneratedRoadmapLesson): string | undefined {
  if (lesson.summary && lesson.summary.trim()) return lesson.summary
  const count = lesson.concepts?.length ?? 0
  if (!count) return undefined
  return `${count} concept${count === 1 ? '' : 's'}`
}

function toConcept(c: GeneratedRoadmapConcept): HomeRoadmapConcept {
  return {
    id: String(c.id ?? c.name ?? ''),
    name: c.name ?? c.id ?? '',
    description: c.description,
    status: stateToStatus(c.state),
  }
}

function makeLessonOutcomes(roadmap: GeneratedRoadmap | undefined): HomeRoadmapOutcome[] {
  const lessons = roadmap?.lessons ?? []
  return lessons.map((lesson) => ({
    id: lesson.lesson_id,
    title: lesson.title,
    status: stateToStatus(lesson.state),
    subtext: lessonSubtext(lesson),
    concepts: (lesson.concepts ?? []).map(toConcept),
  }))
}

export default function RoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [data, setData] = useState<RoadmapData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const { studentId } = usePersona()
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setData(null)
    setError(null)
    fetchStudentRoadmapData(studentId)
      .then((next) => {
        if (!cancelled) setData(next)
      })
      .catch((err) => {
        if (!cancelled) setError(String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  const outcomes = useMemo(() => makeLessonOutcomes(data?.roadmap), [data?.roadmap])
  const activeLesson = useMemo(
    () => (data?.roadmap.lessons ?? []).find((lesson) => lesson.state === 'active'),
    [data?.roadmap.lessons],
  )
  const title = data?.student.learning_goals?.target_course || data?.student.learning_goals?.primary_focus || 'Roadmap'
  const description = `${outcomes.length} lesson${outcomes.length === 1 ? '' : 's'} · Personalized for you`

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
      title={title}
      description={description}
    >
      <div className="max-w-[800px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        {error && (
          <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            Failed to load roadmap: {error}
          </div>
        )}
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-24 text-gray-400 dark:text-gray-500">
            <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            <p className="text-sm">Building your personalized roadmap…</p>
          </div>
        ) : (
          <LearningRoadmap
            outcomes={outcomes.length ? outcomes : []}
            startHereTo={activeLesson ? `/lesson?lesson_id=${encodeURIComponent(activeLesson.lesson_id)}` : '#'}
            onStartHere={handleStartHere}
            buildTranscriptHref={(concept) =>
              `/lesson/transcript?student_id=${encodeURIComponent(studentId)}&concept_id=${encodeURIComponent(concept.id)}`
            }
          />
        )}

        <button
          type="button"
          className="fixed bottom-8 right-8 flex items-center gap-2 rounded-2xl bg-primary px-5 py-3 text-white font-bold shadow-lg shadow-primary/30 hover:bg-primary-light hover:shadow-xl transition-all z-10"
        >
          <span className="material-symbols-outlined">help</span>
          Ask anything
        </button>
      </div>
    </AppLayout>
  )
}
