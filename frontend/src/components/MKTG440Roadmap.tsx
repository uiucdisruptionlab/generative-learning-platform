import { Link } from 'react-router-dom'

const OUTCOMES = [
  {
    id: '1',
    title: 'Digital Marketing Fundamentals',
    status: 'completed' as const,
  },
  {
    id: '2',
    title: 'SEO Basics',
    status: 'current' as const,
    subtext: 'Master search engine optimization and content discovery.',
  },
  {
    id: '3',
    title: 'Social Media Strategy',
    status: 'upcoming' as const,
  },
  {
    id: '4',
    title: 'Email Marketing',
    status: 'upcoming' as const,
  },
  {
    id: '5',
    title: 'Analytics and Metrics',
    status: 'upcoming' as const,
  },
  {
    id: '6',
    title: 'Campaign Optimization',
    status: 'upcoming' as const,
  },
]

type MKTG440RoadmapProps = {
  compact?: boolean
  showViewFullLink?: boolean
}

export default function MKTG440Roadmap({ compact, showViewFullLink }: MKTG440RoadmapProps) {
  return (
    <div className="relative pl-1">
      <div className="absolute left-[11px] top-8 bottom-8 w-0 border-l-2 border-dashed border-slate-300 dark:border-slate-600" />
      {OUTCOMES.map((outcome) => (
        <div key={outcome.id} className={`relative flex gap-6 ${compact ? 'pb-6 last:pb-0' : 'pb-10 last:pb-0'}`}>
          <div
            className={`relative z-10 flex shrink-0 items-center justify-center rounded-full ${
              outcome.status === 'completed'
                ? 'bg-primary text-white size-6'
                : outcome.status === 'current'
                  ? 'bg-primary text-white ring-4 ring-primary/20 size-6'
                  : 'bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-600 size-6'
            }`}
          >
            {outcome.status === 'completed' ? (
              <span className="material-symbols-outlined text-sm">check</span>
            ) : outcome.status === 'current' ? (
              <span className="size-2 rounded-full bg-white" />
            ) : (
              <span className="size-2 rounded-full bg-slate-300 dark:bg-slate-500" />
            )}
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3
                  className={`font-bold font-display ${
                    outcome.status === 'upcoming'
                      ? 'text-slate-400 dark:text-slate-500'
                      : 'text-slate-900 dark:text-white'
                  } ${compact ? 'text-base' : 'text-lg'}`}
                >
                  {outcome.title}
                </h3>
                {outcome.subtext && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    {outcome.subtext}
                  </p>
                )}
              </div>
              {outcome.status === 'current' && (
                <Link
                  to="/module/mktg440-seo"
                  className="shrink-0 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light transition-all shadow-md shadow-primary/20 inline-block"
                >
                  Start here
                </Link>
              )}
            </div>
          </div>
        </div>
      ))}
      {showViewFullLink && (
        <div className="mt-6 pl-8">
          <Link
            to="/roadmap/mktg440"
            className="text-sm font-semibold text-primary hover:underline inline-flex items-center gap-1"
          >
            View full roadmap
            <span className="material-symbols-outlined text-lg">arrow_forward</span>
          </Link>
        </div>
      )}
    </div>
  )
}
