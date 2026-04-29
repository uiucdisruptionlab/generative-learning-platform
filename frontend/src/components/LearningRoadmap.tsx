import { Link } from 'react-router-dom'
import { MouseEvent, useEffect, useMemo, useRef, useState } from 'react'
import type {
  HomeRoadmapConcept,
  HomeRoadmapOutcome,
  HomeRoadmapStatus,
} from '../data/homeRoadmapPreview'

type LearningRoadmapProps = {
  compact?: boolean
  showViewFullLink?: boolean
  /** When true, list is capped in height and scrolls; current step is scrolled into view. */
  scrollable?: boolean
  outcomes?: HomeRoadmapOutcome[]
  startHereTo?: string
  viewFullTo?: string
  onStartHere?: (event: MouseEvent<HTMLAnchorElement>) => void
  /**
   * Builds the destination for the "View transcript" link on a completed concept.
   * Return `null`/`undefined` to hide the link.
   */
  buildTranscriptHref?: (concept: HomeRoadmapConcept, outcome: HomeRoadmapOutcome) => string | null | undefined
}

function lessonDotClasses(status: HomeRoadmapStatus): string {
  if (status === 'completed') return 'bg-primary text-white size-6'
  if (status === 'current') return 'bg-primary text-white ring-4 ring-primary/20 size-6'
  return 'bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-600 size-6'
}

function ConceptRow({
  concept,
  href,
}: {
  concept: HomeRoadmapConcept
  href?: string | null
}) {
  const isCompleted = concept.status === 'completed'
  const isCurrent = concept.status === 'current'
  const dot = (
    <span
      className={`relative z-10 flex shrink-0 items-center justify-center rounded-full size-4 ${
        isCompleted
          ? 'bg-primary/80 text-white'
          : isCurrent
            ? 'bg-primary text-white ring-2 ring-primary/20'
            : 'bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600'
      }`}
    >
      {isCompleted ? (
        <span className="material-symbols-outlined text-[10px] leading-none">check</span>
      ) : isCurrent ? (
        <span className="size-1.5 rounded-full bg-white" />
      ) : (
        <span className="size-1.5 rounded-full bg-slate-300 dark:bg-slate-500" />
      )}
    </span>
  )

  const label = (
    <span
      className={`text-sm ${
        concept.status === 'upcoming'
          ? 'text-slate-400 dark:text-slate-500'
          : isCurrent
            ? 'text-slate-900 dark:text-white font-semibold'
            : 'text-slate-700 dark:text-slate-200'
      }`}
    >
      {concept.name}
    </span>
  )

  return (
    <li className="flex items-center gap-3 py-1.5">
      {dot}
      <div className="flex-1 min-w-0 flex items-center justify-between gap-3">
        {label}
        {isCompleted && href ? (
          <Link
            to={href}
            className="shrink-0 text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
          >
            View
            <span className="material-symbols-outlined text-sm leading-none">chevron_right</span>
          </Link>
        ) : null}
      </div>
    </li>
  )
}

export default function LearningRoadmap({
  compact,
  showViewFullLink,
  scrollable,
  outcomes: outcomesProp,
  startHereTo = '#',
  viewFullTo = '/roadmap',
  onStartHere,
  buildTranscriptHref,
}: LearningRoadmapProps) {
  const outcomes = outcomesProp ?? []
  const currentItemRef = useRef<HTMLDivElement | null>(null)

  // Auto-expand the active lesson; let the user toggle the rest. Re-derive when
  // outcomes change so a new active lesson opens even after a roadmap rebuild.
  const activeId = useMemo(() => outcomes.find((o) => o.status === 'current')?.id, [outcomes])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  useEffect(() => {
    if (activeId) setExpanded((prev) => ({ ...prev, [activeId]: true }))
  }, [activeId])

  useEffect(() => {
    if (!scrollable || !currentItemRef.current) return
    const id = requestAnimationFrame(() => {
      currentItemRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(id)
  }, [scrollable, outcomes])

  const empty = (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-slate-400 dark:text-slate-500">
      <span className="material-symbols-outlined text-3xl text-primary/60">route</span>
      <p className={`font-semibold ${compact ? 'text-sm' : 'text-base'} text-slate-500 dark:text-slate-400`}>
        Your roadmap is being prepared.
      </p>
      <p className="text-xs text-slate-400 dark:text-slate-500">
        Check back in a moment, or rebuild it from your profile.
      </p>
    </div>
  )

  const list = (
    <div className="relative pl-1">
      <div className="absolute left-[11px] top-8 bottom-8 w-0 border-l-2 border-dashed border-slate-300 dark:border-slate-600" />
      {outcomes.map((outcome) => {
        const concepts = outcome.concepts ?? []
        const hasConcepts = concepts.length > 0
        const isOpen = expanded[outcome.id] ?? false
        return (
          <div
            key={outcome.id}
            ref={outcome.status === 'current' ? currentItemRef : undefined}
            className={`relative flex gap-6 ${compact ? 'pb-6 last:pb-0' : 'pb-10 last:pb-0'}`}
          >
            <div className={`relative z-10 flex shrink-0 items-center justify-center rounded-full ${lessonDotClasses(outcome.status)}`}>
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
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3
                      className={`font-bold font-display ${
                        outcome.status === 'upcoming'
                          ? 'text-slate-400 dark:text-slate-500'
                          : 'text-slate-900 dark:text-white'
                      } ${compact ? 'text-base' : 'text-lg'}`}
                    >
                      {outcome.title}
                    </h3>
                    {hasConcepts && (
                      <button
                        type="button"
                        onClick={() => setExpanded((prev) => ({ ...prev, [outcome.id]: !isOpen }))}
                        className="inline-flex items-center justify-center rounded-md text-slate-400 hover:text-primary hover:bg-primary/10 size-6 transition-colors"
                        aria-expanded={isOpen}
                        aria-label={isOpen ? 'Collapse concepts' : 'Expand concepts'}
                      >
                        <span className={`material-symbols-outlined text-lg leading-none transition-transform ${isOpen ? 'rotate-180' : ''}`}>
                          expand_more
                        </span>
                      </button>
                    )}
                  </div>
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
              {hasConcepts && isOpen && (
                <ul className="mt-3 space-y-0.5 border-l-2 border-dotted border-slate-200 dark:border-slate-700 pl-4">
                  {concepts.map((concept) => (
                    <ConceptRow
                      key={concept.id}
                      concept={concept}
                      href={buildTranscriptHref?.(concept, outcome) ?? undefined}
                    />
                  ))}
                </ul>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )

  const body = outcomes.length === 0 ? empty : list

  return (
    <div>
      {scrollable ? (
        <div className="max-h-[min(11rem,27vh)] overflow-y-auto overscroll-y-contain scroll-smooth rounded-xl border border-industrial/45 dark:border-industrial/30 bg-stone-50/50 dark:bg-slate-950/30 px-3 py-2 sm:px-4">
          {body}
        </div>
      ) : (
        body
      )}
      {showViewFullLink && (
        <div className={`mt-6 pl-8 ${scrollable ? 'border-t border-industrial/35 dark:border-industrial/25 pt-4' : ''}`}>
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
