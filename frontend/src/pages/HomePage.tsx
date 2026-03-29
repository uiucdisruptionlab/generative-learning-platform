import { useState } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import RoadmapCourseSelect from '../components/RoadmapCourseSelect'
import { HOME_ROADMAP_PREVIEW } from '../data/homeRoadmapPreview'

export default function HomePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [homeRoadmapPath, setHomeRoadmapPath] = useState('/roadmap')
  const roadmapPreview = HOME_ROADMAP_PREVIEW[homeRoadmapPath] ?? HOME_ROADMAP_PREVIEW['/roadmap']

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Home"
      description="Your personalized learning hub and AI-enhanced recommendations."
    >
      <div className="max-w-[1200px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12 space-y-8">
        <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft bg-gradient-to-br from-white via-amber-50/20 to-white dark:from-slate-900 dark:via-slate-900/50 dark:to-slate-900">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white font-display">Welcome back, Alex.</h1>
              <p className="text-slate-500 dark:text-slate-400 font-medium">Your personalized learning path is <span className="text-primary font-bold">65% complete</span>. You're ahead of 82% of your cohort.</p>
            </div>
            <div className="flex gap-3">
              <button className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light transition-all shadow-md shadow-primary/20">Resume Learning</button>
              <button className="rounded-xl border-2 border-primary/30 px-5 py-2.5 text-sm font-bold text-primary hover:bg-primary/10 dark:hover:bg-primary/20 transition-colors">View Full Path</button>
            </div>
          </div>
          <div className="mt-8 space-y-3">
            <div className="flex justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Core Fundamentals</span>
              <span>Advanced Specialization</span>
            </div>
            <div className="relative h-4 w-full overflow-hidden rounded-full bg-stone-200/80 dark:bg-slate-800">
              <div className="absolute h-full w-[65%] rounded-full bg-gradient-to-r from-primary to-primary-light shadow-lg shadow-primary/30" />
              <div className="absolute inset-0 flex">
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4 border-r border-white/20" />
                <div className="w-1/4" />
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-8 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-5">
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
                <span className="material-symbols-outlined text-primary shrink-0">route</span>
                <span className="break-words">{roadmapPreview.cardTitle}</span>
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {roadmapPreview.cardSubtitle}
              </p>
            </div>
            <RoadmapCourseSelect
              variant="page"
              value={homeRoadmapPath}
              onValueChange={setHomeRoadmapPath}
              className="w-full lg:w-auto lg:max-w-md shrink-0"
            />
          </div>
          <LearningRoadmap
            key={homeRoadmapPath}
            compact
            showViewFullLink
            scrollable
            outcomes={roadmapPreview.outcomes}
            startHereTo={roadmapPreview.startHerePath}
            viewFullTo={roadmapPreview.fullRoadmapPath}
          />
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 min-w-0">
          <div className="xl:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 font-display">
                <span className="material-symbols-outlined text-primary">auto_awesome</span>
                Top Recommendations for You
              </h2>
              <button className="text-sm font-semibold text-primary hover:underline">Customize feed</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="group flex flex-col rounded-2xl bg-white/95 dark:bg-slate-900/95 border border-emerald-200/70 dark:border-emerald-700/40 p-4 shadow-soft hover:border-primary/60 hover:shadow-xl hover:shadow-primary/10 transition-all duration-300">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                  <span className="material-symbols-outlined">monitoring</span>
                </div>
                <span className="mb-2 inline-flex items-center rounded bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">Tech Interest</span>
                <h3 className="mb-4 text-sm font-bold text-stone-900 dark:text-white leading-snug font-display">Advanced Financial Modeling Activity</h3>
                <div className="mt-auto flex items-center justify-between">
                  <span className="text-xs text-stone-400">45 min activity</span>
                  <span className="material-symbols-outlined text-stone-300 group-hover:text-primary">arrow_forward</span>
                </div>
              </div>
              <div className="group flex flex-col rounded-2xl bg-white dark:bg-slate-900 border-2 border-amber-200/70 dark:border-amber-700/40 p-4 shadow-soft hover:border-secondary/60 transition-all hover:shadow-hover-soft">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-900/30 text-secondary group-hover:bg-secondary group-hover:text-white transition-colors">
                  <span className="material-symbols-outlined">auto_stories</span>
                </div>
                <span className="mb-2 inline-flex items-center rounded bg-amber-50 dark:bg-amber-900/30 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-secondary">Deep Dive</span>
                <h3 className="mb-4 text-sm font-bold text-stone-900 dark:text-white leading-snug font-display">Sustainability in Supply Chain - Required Reading</h3>
                <div className="mt-auto flex items-center justify-between">
                  <span className="text-xs text-stone-400">12 page PDF</span>
                  <span className="material-symbols-outlined text-stone-300 group-hover:text-secondary">arrow_forward</span>
                </div>
              </div>
              <div className="group flex flex-col rounded-2xl bg-white dark:bg-slate-900 border border-orange-200/70 dark:border-orange-700/40 p-4 shadow-soft hover:border-accent/60 transition-all hover:shadow-hover-soft">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-orange-50 dark:bg-orange-900/30 text-accent group-hover:bg-accent group-hover:text-white transition-colors">
                  <span className="material-symbols-outlined">play_circle</span>
                </div>
                <span className="mb-2 inline-flex items-center rounded bg-orange-50 dark:bg-orange-900/30 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">Video Lesson</span>
                <h3 className="mb-4 text-sm font-bold text-stone-900 dark:text-white leading-snug font-display">Foundations of Quantitative Analysis</h3>
                <div className="mt-auto flex items-center justify-between">
                  <span className="text-xs text-stone-400">18 min video</span>
                  <span className="material-symbols-outlined text-stone-300 group-hover:text-accent">arrow_forward</span>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border-2 border-indigo-200/70 dark:border-indigo-700/40 bg-white/95 dark:bg-slate-900/95 p-6 shadow-sm bg-gradient-to-br from-white via-indigo-50/10 to-white dark:from-slate-900 dark:via-indigo-950/20 dark:to-slate-900">
              <div className="mb-8 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white font-display">Personal Skill Growth</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Your progress is automatically synced to guide your next steps.</p>
                </div>
                <span className="material-symbols-outlined text-slate-300 cursor-help">info</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                <div className="relative mx-auto flex h-56 w-56 items-center justify-center">
                  <div className="absolute h-full w-full rounded-full border border-slate-50 dark:border-slate-800" />
                  <div className="absolute h-3/4 w-3/4 rounded-full border border-slate-50 dark:border-slate-800" />
                  <div className="absolute h-1/2 w-1/2 rounded-full border border-slate-50 dark:border-slate-800" />
                  <div className="skill-radar absolute inset-0 bg-indigo-500/10 border-2 border-indigo-400/30" />
                </div>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-wider">
                      <span>Financial Modeling</span>
                      <span className="text-primary">85%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full w-[85%] rounded-full bg-primary" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-wider">
                      <span>Supply Chain Mgmt</span>
                      <span className="text-secondary">72%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full w-[72%] rounded-full bg-secondary" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-wider">
                      <span>Data Visualization</span>
                      <span className="text-accent">40%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full w-[40%] rounded-full bg-accent" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 font-display">
              <span className="material-symbols-outlined text-primary">event_note</span>
              Upcoming Milestones
            </h2>
            <div className="rounded-2xl border border-primary/20 dark:border-primary/30 bg-white dark:bg-slate-900 p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200">October 2023</span>
                <div className="flex gap-2">
                  <span className="material-symbols-outlined text-lg text-slate-400 cursor-pointer">chevron_left</span>
                  <span className="material-symbols-outlined text-lg text-slate-400 cursor-pointer">chevron_right</span>
                </div>
              </div>
              <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-bold text-slate-400 uppercase mb-2">
                <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
              </div>
              <div className="grid grid-cols-7 gap-1 text-center">
                <div className="p-1 text-xs text-slate-300">25</div>
                <div className="p-1 text-xs text-slate-300">26</div>
                <div className="p-1 text-xs text-slate-300">27</div>
                <div className="p-1 text-xs text-slate-300">28</div>
                <div className="p-1 text-xs text-slate-300">29</div>
                <div className="p-1 text-xs text-slate-300">30</div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">1</div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">2</div>
                <div className="p-1 text-xs font-bold text-primary ring-1 ring-primary rounded-md">3</div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">4</div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">5</div>
                <div className="relative p-1 text-xs text-slate-800 dark:text-slate-300 font-bold">6<span className="absolute bottom-0 left-1/2 -translate-x-1/2 h-1 w-1 rounded-full bg-red-500" /></div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">7</div>
                <div className="p-1 text-xs text-slate-800 dark:text-slate-300">8</div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex gap-4 rounded-xl border-l-4 border-red-400 bg-white dark:bg-slate-900 p-4 shadow-sm border-2 border-red-100 dark:border-red-900/40">
                <div className="flex-1 space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-red-500">High Priority</p>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">Midterm Project Submission</h4>
                  <p className="text-xs text-slate-500">Due in 3 days • Econ 301</p>
                </div>
              </div>
              <div className="flex gap-4 rounded-xl border-l-4 border-primary bg-white dark:bg-slate-900 p-4 shadow-sm border-2 border-emerald-100 dark:border-emerald-900/40">
                <div className="flex-1 space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-primary">Assessment</p>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">Quiz: Macroeconomics</h4>
                  <p className="text-xs text-slate-500">Friday, Oct 6 • 10:00 AM</p>
                </div>
              </div>
              <div className="flex gap-4 rounded-xl border-l-4 border-slate-300 bg-white dark:bg-slate-900 p-4 shadow-sm border-2 border-slate-200 dark:border-slate-700">
                <div className="flex-1 space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Study Reminder</p>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">Review Case Study 4</h4>
                  <p className="text-xs text-slate-500">Personal Goal • Strategic Mgmt</p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 p-6 border-2 border-emerald-100 dark:border-emerald-800 shadow-soft">
              <div className="flex items-start justify-between mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white dark:bg-slate-900 shadow-sm">
                  <span className="material-symbols-outlined text-primary">tips_and_updates</span>
                </div>
                <button className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"><span className="material-symbols-outlined text-lg">close</span></button>
              </div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 font-display">Personalized Study Tip</h4>
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300 font-medium">Based on your recent scores, focusing on <span className="text-primary font-bold">&quot;Exchange Rate Theory&quot;</span> could improve your upcoming quiz grade by ~15%.</p>
              <button className="mt-4 w-full rounded-xl bg-white dark:bg-slate-900 border-2 border-emerald-200 dark:border-emerald-800 py-2.5 text-xs font-bold text-primary hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-all shadow-sm">Add to Study Plan</button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
