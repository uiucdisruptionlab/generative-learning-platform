import { useState } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import { HOME_ROADMAP_PREVIEW } from '../data/homeRoadmapPreview'

export default function AccountingRoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const roadmapData = HOME_ROADMAP_PREVIEW['/roadmap/accounting']

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
        <LearningRoadmap
          outcomes={roadmapData.outcomes}
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
