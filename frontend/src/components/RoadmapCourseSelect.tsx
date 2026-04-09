import { useNavigate, useLocation } from 'react-router-dom'

export const ROADMAP_COURSES = [
  { path: '/roadmap', label: 'ACCY 301 · Financial Accounting' },
  { path: '/roadmap/cs101', label: 'CS 101 · Intro to Python' },
] as const

type RoadmapCourseSelectProps = {
  /** Compact styling for PageHeader (green gradient bar) */
  variant?: 'page' | 'header'
  value?: string
  onValueChange?: (path: string) => void
  className?: string
  selectId?: string
}

export default function RoadmapCourseSelect({
  variant = 'page',
  value: controlledValue,
  onValueChange,
  className: rootClassName,
  selectId,
}: RoadmapCourseSelectProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const isControlled = controlledValue !== undefined && onValueChange !== undefined

  const value = isControlled
    ? controlledValue
    : (ROADMAP_COURSES.find((c) => c.path === location.pathname)?.path ?? '/roadmap')

  const isHeader = variant === 'header'
  const selectDomId = selectId ?? (isControlled ? 'roadmap-course-home' : 'roadmap-course')

  return (
    <div
      className={`${isHeader ? '' : isControlled ? 'mb-0' : 'mb-8'} ${rootClassName ?? ''}`.trim()}
    >
      <label htmlFor={selectDomId} className="sr-only">
        Choose course roadmap
      </label>
      <div
        className={
          isHeader
            ? 'flex flex-col sm:flex-row sm:items-center gap-2 w-full md:w-auto md:min-w-[260px] max-w-md'
            : 'flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4'
        }
      >
        <span
          className={
            isHeader
              ? 'sr-only'
              : 'text-sm font-semibold text-slate-600 dark:text-slate-400 shrink-0'
          }
        >
          Course
        </span>
        <select
          id={selectDomId}
          value={value}
          onChange={(e) =>
            isControlled ? onValueChange(e.target.value) : navigate(e.target.value)
          }
          className={
            isHeader
              ? 'w-full rounded-xl border border-emerald-800/20 dark:border-white/25 bg-white/90 dark:bg-slate-900/75 backdrop-blur-sm px-3 py-2.5 text-sm font-semibold text-slate-900 dark:text-white shadow-sm focus:border-primary dark:focus:border-primary/60 focus:outline-none focus:ring-2 focus:ring-primary/25 cursor-pointer'
              : 'w-full sm:max-w-md rounded-xl border-2 border-primary/20 dark:border-primary/30 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-semibold text-slate-900 dark:text-white shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer'
          }
        >
          {ROADMAP_COURSES.map((course) => (
            <option key={course.path} value={course.path}>
              {course.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
