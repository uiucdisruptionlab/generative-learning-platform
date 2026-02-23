import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import PageHeader from './PageHeader'

type AppLayoutProps = {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  settingsOpen: boolean
  onToggleSettings: () => void
  title: string
  description: string
  action?: ReactNode
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
  children,
}: AppLayoutProps) {
  const location = useLocation()

  return (
    <div className="flex min-h-screen overflow-x-hidden bg-gradient-to-br from-stone-50 via-amber-50/30 to-stone-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 font-sans text-slate-800 dark:text-slate-100 antialiased">
      <aside
        className={`w-72 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-r-2 border-primary/15 dark:border-primary/20 flex flex-col fixed h-full transition-transform duration-300 z-30 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-8">
          <div className="flex items-center gap-4 mb-10">
            <div className="size-12 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary ring-1 ring-primary/20">
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
                  ? 'bg-gradient-to-r from-primary to-primary-light text-white shadow-lg shadow-primary/25'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">home</span>
              <span className="text-sm font-semibold">Home</span>
            </Link>
            <Link
              to="/dashboard"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname === '/dashboard'
                  ? 'bg-gradient-to-r from-primary to-primary-light text-white shadow-lg shadow-primary/25'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">work</span>
              <span className="text-sm font-semibold">Career Hub</span>
            </Link>
            <Link
              to="/courses"
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all group ${
                location.pathname === '/courses'
                  ? 'bg-gradient-to-r from-primary to-primary-light text-white shadow-lg shadow-primary/25'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">book</span>
              <span className="text-sm font-semibold">My Courses</span>
            </Link>
            <a href="#" className="flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all group">
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">ads_click</span>
              <span className="text-sm font-semibold">Skills Path</span>
            </a>
            <a href="#" className="flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all group">
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">assignment</span>
              <span className="text-sm font-semibold">Assignments</span>
            </a>
            <a href="#" className="flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all group">
              <span className="material-symbols-outlined group-hover:text-primary transition-colors">bar_chart</span>
              <span className="text-sm font-semibold">Performance</span>
            </a>
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
            <div
              className="size-11 rounded-full bg-slate-200 dark:bg-slate-700 bg-cover bg-center ring-2 ring-white dark:ring-slate-900 shadow-sm"
              style={{
                backgroundImage:
                  "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDs46P0CZ3XO6IpxwKmlWOzkVVgpzXbgHshy0mB95PNbmEuNjREXUdGTy9uWs4yL3WiG3k00SqntZWP9ixeKoRrYw5KHge_gn69LU_absQEGK1VHQV2U2Hm91HQgAvIEcTdkchtjKtU3U0fEOjxezLIcdu7x_L7-Tz20vYYx_xU6J42r9a2hhztQsm447XonCJkerJtP3lzUzSUoJoLLeU1LObC2wSaNzunidTHSlUSIJ6zNtLTVDYumNRFEUtqAn65QR-AmQ4b9qsw')",
              }}
            />
            <div className="flex flex-col">
              <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight">Alex Johnson</p>
              <p className="text-[11px] text-slate-400 font-medium">Student ID: 882104</p>
            </div>
          </div>
        </div>
      </aside>

      <main className={`flex-1 min-w-0 transition-all duration-300 ${sidebarOpen ? 'ml-72' : 'ml-0'}`}>
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
