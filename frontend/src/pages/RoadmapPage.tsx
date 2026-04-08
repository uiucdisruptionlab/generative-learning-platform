import { useState, useEffect } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import RoadmapCourseSelect from '../components/RoadmapCourseSelect'
import {
  fetchRoadmap,
  mapLessonsToOutcomes,
  ROADMAP_TARGETS,
  type FrontendRoadmapTarget,
} from '../api/roadmap'
import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'

export default function RoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [outcomes, setOutcomes] = useState<HomeRoadmapOutcome[] | null>(null)
  const [target, setTarget] = useState<FrontendRoadmapTarget>(ROADMAP_TARGETS.accounting)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchRoadmap({ ...target, refine: true })
      .then((data) => {
        setOutcomes(mapLessonsToOutcomes(data.lessons))
        setError(null)
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [target])

  const outcomeCount = outcomes ? `${outcomes.length} learning outcomes` : '...'

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Financial Accounting"
      description={`${outcomeCount} · Personalized for you`}
      action={<RoadmapCourseSelect variant="header" onValueChange={(path) => {
        if (path === '/roadmap/accounting' || path === '/roadmap') {
          setTarget(ROADMAP_TARGETS.accounting)
        } else if (path === '/roadmap/python' || path === '/roadmap/cs101') {
          setTarget(ROADMAP_TARGETS.python)
        } else if (path === '/roadmap/financing') {
          setTarget(ROADMAP_TARGETS.financing)
        }
      }} />}
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
          <LearningRoadmap outcomes={outcomes ?? undefined} />
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
