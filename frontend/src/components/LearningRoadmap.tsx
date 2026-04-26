import { Link } from 'react-router-dom'
import { MouseEvent, useEffect, useRef } from 'react'
import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'

const DEFAULT_OUTCOMES: HomeRoadmapOutcome[] = [
  {
    id: '1',
    title: 'Reading a Financial Statement',
    status: 'completed',
  },
  {
    id: '2',
    title: 'The Income Statement',
    status: 'current',
    subtext: 'Based on your background, this is the right place to start.',
  },
  {
    id: '3',
    title: 'The Balance Sheet',
    status: 'upcoming',
  },
  {
    id: '4',
    title: 'Cash Flow Basics',
    status: 'upcoming',
  },
  {
    id: '5',
    title: 'Ratio Analysis',
    status: 'upcoming',
  },
  {
    id: '6',
    title: 'Interpreting Performance',
    status: 'upcoming',
  },
]

type LearningRoadmapProps = {
  compact?: boolean
  showViewFullLink?: boolean
  /** When true, list is capped in height and scrolls; current step is scrolled into view. */
  scrollable?: boolean
  outcomes?: HomeRoadmapOutcome[]
  startHereTo?: string
  viewFullTo?: string
  onStartHere?: (event: MouseEvent<HTMLAnchorElement>) => void
}

export default function LearningRoadmap({
  compact,
  showViewFullLink,
  scrollable,
  outcomes: outcomesProp,
  startHereTo = '/module/income-statement',
  viewFullTo = '/roadmap',
  onStartHere,
}: LearningRoadmapProps) {
  const outcomes = outcomesProp ?? DEFAULT_OUTCOMES
  const currentItemRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!scrollable || !currentItemRef.current) return
    const id = requestAnimationFrame(() => {
      currentItemRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(id)
  }, [scrollable, outcomes])

  const list = (
    <div className="relative pl-1">
      <div className="absolute left-[11px] top-8 bottom-8 w-0 border-l-2 border-dashed border-slate-300 dark:border-slate-600" />
      {outcomes.map((outcome) => (
        <div
          key={outcome.id}
          ref={outcome.status === 'current' ? currentItemRef : undefined}
          className={`relative flex gap-6 ${compact ? 'pb-6 last:pb-0' : 'pb-10 last:pb-0'}`}
        >
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
                  to={startHereTo}
                  onClick={onStartHere}
                  className="shrink-0 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light transition-all shadow-md shadow-primary/20 inline-block"
                >
                  Start here
                </Link>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <div>
      {scrollable ? (
        <div className="max-h-[min(11rem,27vh)] overflow-y-auto overscroll-y-contain scroll-smooth rounded-xl border border-emerald-200/60 dark:border-emerald-800/40 bg-stone-50/50 dark:bg-slate-950/30 px-3 py-2 sm:px-4">
          {list}
        </div>
      ) : (
        list
      )}
      {showViewFullLink && (
        <div className={`mt-6 pl-8 ${scrollable ? 'border-t border-emerald-200/40 dark:border-emerald-800/30 pt-4' : ''}`}>
          <Link
            to={viewFullTo}
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
