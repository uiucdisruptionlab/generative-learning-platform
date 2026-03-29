import { useState } from 'react'
import AppLayout from '../components/AppLayout'
import CS101Roadmap from '../components/CS101Roadmap'
import RoadmapCourseSelect from '../components/RoadmapCourseSelect'

export default function CS101RoadmapPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Intro to Python"
      description="6 learning outcomes · Personalized for you"
      action={<RoadmapCourseSelect variant="header" />}
    >
      <div className="max-w-[800px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        <CS101Roadmap />

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
