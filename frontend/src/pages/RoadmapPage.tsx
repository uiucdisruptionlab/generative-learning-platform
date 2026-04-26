import { MouseEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'
import { usePersona } from '../contexts/PersonaContext'
import { fetchStudentRoadmapData, startSession, type GeneratedRoadmapConcept } from '../api/home'

type RoadmapData = Awaited<ReturnType<typeof fetchStudentRoadmapData>>

function conceptTitle(nodeId: string, concepts: GeneratedRoadmapConcept[] = []): string {
  const found = concepts.find((concept) => concept.id === nodeId || concept.name === nodeId)
  return found?.name || found?.id || nodeId
}

function conceptDescription(nodeId: string, concepts: GeneratedRoadmapConcept[] = []): string | undefined {
  const found = concepts.find((concept) => concept.id === nodeId || concept.name === nodeId)
  return found?.description
}

function makeOutcomes(
  nodeIds: string[],
  concepts: GeneratedRoadmapConcept[] | undefined,
  currentIndex: number,
): HomeRoadmapOutcome[] {
  return nodeIds.map((nodeId, index) => ({
    id: nodeId,
    title: conceptTitle(nodeId, concepts),
    status: index < currentIndex ? 'completed' : index === currentIndex ? 'current' : 'upcoming',
    subtext: conceptDescription(nodeId, concepts),
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

  const currentIndex = data?.roadmapPosition.current_index ?? 0
  const nodeIds = data?.roadmap.node_ids ?? []
  const outcomes = useMemo(
    () => makeOutcomes(nodeIds, data?.roadmap.concepts, currentIndex),
    [nodeIds, data?.roadmap.concepts, currentIndex],
  )
  const activeNodeId = nodeIds[Math.min(Math.max(currentIndex, 0), Math.max(nodeIds.length - 1, 0))]
  const title = data?.student.learning_goals?.target_course || data?.student.learning_goals?.primary_focus || 'Roadmap'
  const description = `${outcomes.length} learning outcomes · Personalized for you`

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
            startHereTo={activeNodeId ? `/lesson/${activeNodeId}/interactive` : '#'}
            onStartHere={handleStartHere}
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
