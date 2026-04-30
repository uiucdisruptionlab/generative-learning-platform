import { ReactNode } from 'react'

type PageHeaderProps = {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  title: string
  description: string
  action?: ReactNode
}

export default function PageHeader({ sidebarOpen, onToggleSidebar, title, description, action }: PageHeaderProps) {
  return (
    <header className="bg-gradient-to-r from-illini-blue via-illini-blue to-industrial/90 backdrop-blur-xl sticky top-0 z-20 border-b-2 border-industrial/55 dark:border-industrial/45 px-8 py-8 sm:px-12 sm:py-10 shrink-0">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 min-w-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-white/90 hover:bg-white/10 transition-colors shrink-0"
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <span className="material-symbols-outlined">{sidebarOpen ? 'chevron_left' : 'menu'}</span>
          </button>
          <div className="min-w-0">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight break-words font-display">
              {title}
            </h2>
            <p className="text-white/75 mt-2 text-base sm:text-lg">
              {description}
            </p>
          </div>
        </div>
        {action && (
          <div className="shrink-0">
            {action}
          </div>
        )}
      </div>
    </header>
  )
}
