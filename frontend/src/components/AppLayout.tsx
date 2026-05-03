import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import PageHeader from './PageHeader'
import PersonaToggle from './PersonaToggle'
import { usePersona } from '../contexts/PersonaContext'
import { getSidebarProfile } from '../data/personas'

type AppLayoutProps = {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  settingsOpen: boolean
  onToggleSettings: () => void
  title: string
  description: string
  action?: ReactNode
  sidebarProfileOverride?: {
    displayName?: string
    studentId?: string
  }
  children: ReactNode
}

export default function AppLayout({
  sidebarOpen,
  onToggleSidebar,
  settingsOpen,
  onToggleSettings,
  title,
  description,
  action,
  sidebarProfileOverride,
  children,
}: AppLayoutProps) {
  const location = useLocation()
  const { currentPersona, setCurrentPersona } = usePersona()
  const sidebarProfile = getSidebarProfile(currentPersona)
  const displayName = sidebarProfileOverride?.displayName ?? sidebarProfile?.displayName ?? sidebarProfile?.name ?? 'Learner'
  const studentId = sidebarProfileOverride?.studentId ?? sidebarProfile?.studentId ?? sidebarProfile?.id ?? 'unknown'
  const avatarUrl = sidebarProfile?.avatarUrl ?? ''

  return (
    <div className="flex min-h-screen overflow-x-hidden bg-gradient-to-br from-stone-50 via-storm-300/25 to-stone-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 font-sans text-slate-800 dark:text-slate-100 antialiased">
      <PersonaToggle currentPersona={currentPersona} onPersonaChange={setCurrentPersona} />
      <aside
        className={`w-72 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-r-2 border-industrial/25 dark:border-industrial/30 flex flex-col fixed h-full transition-transform duration-300 z-30 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-8">
          <div className="flex items-center gap-4 mb-10">
            <div className="size-12 rounded-2xl bg-gradient-to-br from-illini-blue/15 to-primary/10 flex items-center justify-center text-illini-blue ring-1 ring-industrial/25">
              <span className="material-symbols-outlined text-3xl font-light">rocket_launch</span>
            </div>
            <div className="flex flex-col">
              <h1 className="text-slate-900 dark:text-white text-base font-bold leading-tight font-logo tracking-normal">Generative Learning Platform</h1>
            </div>
          </div>
          <nav className="space-y-1.5">
            <Link
              to="/home"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname === '/home'
                  ? 'bg-primary/10 dark:bg-primary/20 border-l-4 border-primary text-primary shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">home</span>
              <span className="text-sm font-semibold">Home</span>
            </Link>
            <Link
              to="/roadmap"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname.startsWith('/roadmap')
                  ? 'bg-primary/10 dark:bg-primary/20 border-l-4 border-primary text-primary shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">route</span>
              <span className="text-sm font-semibold">Roadmap</span>
            </Link>
            <Link
              to="/courses"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname === '/courses'
                  ? 'bg-primary/10 dark:bg-primary/20 border-l-4 border-primary text-primary shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">book</span>
              <span className="text-sm font-semibold">My Courses</span>
            </Link>
            <Link
              to="/profile"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname === '/profile'
                  ? 'bg-primary/10 dark:bg-primary/20 border-l-4 border-primary text-primary shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">person</span>
              <span className="text-sm font-semibold">Profile</span>
            </Link>
          </nav>
        </div>
        <div className="mt-auto p-8 pt-0 border-t border-slate-100 dark:border-slate-800">
          <div className="pt-6 pb-6 border-b-2 border-slate-100 dark:border-slate-800">
            <button
              onClick={onToggleSettings}
              className="flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all w-full text-left"
            >
              <span className="material-symbols-outlined">settings</span>
              <span className="text-sm font-semibold">Settings</span>
            </button>
            {settingsOpen && (
              <div className="mt-1 pl-4">
                <Link
                  to="/login"
                  onClick={() => onToggleSettings()}
                  className="flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-primary transition-all"
                >
                  <span className="material-symbols-outlined">logout</span>
                  <span className="text-sm font-semibold">Logout</span>
                </Link>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3.5 px-1 pt-6">
            <img
              src={avatarUrl}
              alt=""
              width={44}
              height={44}
              className="size-11 rounded-full object-cover bg-slate-200 dark:bg-slate-700 ring-2 ring-white dark:ring-slate-900 shadow-sm shrink-0"
            />
            <div className="flex flex-col min-w-0">
              <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight truncate">
                {displayName}
              </p>
              <p className="text-[11px] text-slate-400 font-medium">Student ID: {studentId}</p>
            </div>
          </div>
        </div>
      </aside>

      <main
        className={`flex-1 min-w-0 pb-28 transition-all duration-300 max-[480px]:pb-32 ${sidebarOpen ? 'ml-72' : 'ml-0'}`}
      >
        <PageHeader
          sidebarOpen={sidebarOpen}
          onToggleSidebar={onToggleSidebar}
          title={title}
          description={description}
          action={action}
        />
        {children}
      </main>
    </div>
  )
}
