import { useState, useEffect } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import RoadmapCourseSelect from '../components/RoadmapCourseSelect'
import { fetchRoadmap } from '../api/roadmap'
import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'

const COURSE_ID = 'accounting'

function mapToOutcomes(lessons: { lesson_id: string; title: string; prerequisites: string[] }[]): HomeRoadmapOutcome[] {
  return lessons.map((lesson, index) => ({
    id: lesson.lesson_id,
    title: lesson.title,
    status: index === 0 ? 'current' : 'upcoming',
  }))
}

export default function RoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [outcomes, setOutcomes] = useState<HomeRoadmapOutcome[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRoadmap(COURSE_ID)
      .then((data) => setOutcomes(mapToOutcomes(data.lessons)))
      .catch((err) => setError(String(err)))
  }, [])

  const outcomeCount = outcomes ? `${outcomes.length} learning outcomes` : '...'

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Financial Accounting"
      description={`${outcomeCount} · Personalized for you`}
      action={<RoadmapCourseSelect variant="header" />}
    >
      <div className="max-w-[800px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        {error && (
          <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            Failed to load roadmap: {error}
          </div>
        )}
        <LearningRoadmap outcomes={outcomes ?? undefined} />

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
