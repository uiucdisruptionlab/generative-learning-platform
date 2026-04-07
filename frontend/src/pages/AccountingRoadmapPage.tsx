import { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import { HOME_ROADMAP_PREVIEW } from '../data/homeRoadmapPreview'
import { fetchRoadmap, mapLessonsToOutcomes } from '../api/roadmap'
import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'

export default function AccountingRoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [outcomes, setOutcomes] = useState<HomeRoadmapOutcome[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const roadmapData = HOME_ROADMAP_PREVIEW['/roadmap/accounting']

  useEffect(() => {
    fetchRoadmap({ course: 'accounting' })
      .then((data) => {
        setOutcomes(mapLessonsToOutcomes(data.lessons))
        setError(null)
      })
      .catch((err) => setError(String(err)))
  }, [])

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title={roadmapData.cardTitle}
      description={roadmapData.cardSubtitle}
    >
      <div className="max-w-[800px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        {error && (
          <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            Failed to load roadmap: {error}
          </div>
        )}
        <LearningRoadmap
          outcomes={outcomes ?? roadmapData.outcomes}
          startHereTo={roadmapData.startHerePath}
        />

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
