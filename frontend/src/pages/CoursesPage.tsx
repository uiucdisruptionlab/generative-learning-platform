import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { usePersona } from '../contexts/PersonaContext'
import { fetchCoursesData, type CourseNode } from '../api/home'

type CoursesData = Awaited<ReturnType<typeof fetchCoursesData>>

const GRADIENTS = [
  'from-rose-200 to-red-100 dark:from-rose-800/60 dark:to-red-900/40',
  'from-primary/45 to-emerald-300/70 dark:from-primary/50 dark:to-emerald-400/50',
  'from-amber-200 to-amber-100 dark:from-amber-800/60 dark:to-amber-900/40',
  'from-violet-200 to-purple-100 dark:from-violet-800/60 dark:to-purple-900/40',
  'from-blue-200 to-sky-100 dark:from-blue-800/60 dark:to-sky-900/40',
]

function coursePath(course: CourseNode): string {
  return `/roadmap/${encodeURIComponent(course.id)}`
}

function isActiveCourse(course: CourseNode, activeCourseId: string | undefined): boolean {
  if (!activeCourseId) return false
  return String(course.id) === String(activeCourseId)
}

export default function CoursesPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { studentId } = usePersona()
  const [data, setData] = useState<CoursesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchCoursesData(studentId)
      .then((next) => {
        if (!cancelled) setData(next)
      })
      .catch((err) => {
        if (!cancelled) setError(String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  const courses = data?.courses ?? []

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="My Courses"
      description="Manage your academic workload and AI-enhanced learning paths."
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-12 py-12 lg:py-16 min-w-0">
        <div className="flex flex-col sm:flex-row gap-6 mb-12">
          <div className="relative flex-1">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">search</span>
            <input className="w-full pl-12 pr-6 py-4 bg-white/95 dark:bg-slate-900/95 border-2 border-primary/20 dark:border-primary/30 rounded-2xl focus:ring-4 focus:ring-primary/20 focus:border-primary outline-none text-sm transition-all shadow-sm placeholder:text-slate-400" placeholder="Search your courses..." type="text" />
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-5 py-4 bg-white/95 dark:bg-slate-900/95 border-2 border-primary/20 dark:border-primary/30 rounded-2xl text-sm font-bold text-slate-700 dark:text-slate-300 hover:border-primary/50 hover:shadow-md transition-colors shadow-sm">
              <span>All Semesters</span>
              <span className="material-symbols-outlined text-lg">expand_more</span>
            </button>
            <button className="flex items-center gap-2 px-5 py-4 bg-white/95 dark:bg-slate-900/95 border-2 border-primary/20 dark:border-primary/30 rounded-2xl text-sm font-bold text-slate-700 dark:text-slate-300 hover:border-primary/50 hover:shadow-md transition-colors shadow-sm">
              <span>Sort: Progressive</span>
              <span className="material-symbols-outlined text-lg">sort</span>
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-24 text-gray-400 dark:text-gray-500">
            <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            <p className="text-sm">Loading your courses…</p>
          </div>
        ) : error ? (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            Unable to load courses right now.
          </div>
        ) : courses.length === 0 ? (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            No courses found.
          </div>
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-10 min-w-0">
          {courses.map((course, i) => {
            const active = isActiveCourse(course, data?.roadmap.course_id)
            return (
            <div
              key={course.id}
              className={`group bg-white/95 dark:bg-slate-900/95 rounded-2xl border-2 shadow-[0_4px_20px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_40px_rgb(44,89,38,0.12)] hover:-translate-y-1.5 hover:border-primary/50 transition-all duration-500 overflow-hidden flex flex-col ${
                active
                  ? 'border-primary/60 dark:border-primary/60 ring-2 ring-primary/20'
                  : 'border-primary/20 dark:border-primary/30'
              } ${i >= 3 && !active ? 'opacity-90 hover:opacity-100' : ''}`}
            >
              <div className={`h-32 bg-primary/5 relative overflow-hidden`}>
                <div className={`absolute inset-0 bg-gradient-to-br ${GRADIENTS[i % GRADIENTS.length]}`} />
                {active && (
                  <div className={`absolute top-4 right-4 bg-primary text-white px-2.5 py-1 rounded-lg text-[10px] font-black tracking-widest uppercase shadow-sm`}>
                    Active Course
                  </div>
                )}
              </div>
              <div className="p-6 flex-1 flex flex-col">
                <div className="mb-4">
                  <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${active ? 'text-primary/70' : 'text-slate-400'}`}>{course.course_code || course.id}</span>
                  <h3 className="text-lg font-extrabold text-slate-900 dark:text-white mt-1 leading-tight group-hover:text-primary transition-colors font-display">{course.title}</h3>
                  <p className="text-slate-500 dark:text-slate-400 text-xs mt-1.5 font-medium">{course.professor || ''}</p>
                </div>
                <div className="mt-auto space-y-3">
                  <Link to={coursePath(course)} className="w-full py-3 bg-gradient-to-r from-primary to-primary-light text-white text-sm font-bold rounded-xl flex items-center justify-center gap-2 hover:shadow-xl hover:shadow-primary/30 transition-all shadow-lg shadow-primary/25">
                    <span className="material-symbols-outlined text-xl">rocket_launch</span>
                    Personalized View
                  </Link>
                  <button className="w-full py-3 bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-300 text-sm font-bold rounded-xl border-2 border-slate-200/80 dark:border-slate-700/80 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                    Course Details
                  </button>
                </div>
              </div>
            </div>
          )})}
        </div>
        )}
      </div>
    </AppLayout>
  )
}
