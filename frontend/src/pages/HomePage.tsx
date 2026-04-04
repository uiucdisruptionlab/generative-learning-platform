import { useState } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import { HOME_ROADMAP_PREVIEW } from '../data/homeRoadmapPreview'
import { usePersona } from '../contexts/PersonaContext'

export default function HomePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { currentPersona, persona } = usePersona()

  const homeRoadmapPath = persona ? persona.primaryRoadmapPath : '/roadmap'
  const roadmapPreview = HOME_ROADMAP_PREVIEW[homeRoadmapPath] ?? HOME_ROADMAP_PREVIEW['/roadmap']

  const getPersonaGreeting = () => {
    if (!persona) return 'Alex'
    return persona.name
  }

  const getPersonaProgress = () => {
    if (currentPersona === 'alice') return { progress: 25, percentile: 68 }
    if (currentPersona === 'bob') return { progress: 15, percentile: 55 }
    if (currentPersona === 'charles') return { progress: 45, percentile: 88 }
    return { progress: 65, percentile: 82 }
  }

  const getPersonaSkills = () => {
    if (currentPersona === 'alice') {
      return [
        { name: 'Python Programming', value: 30, color: 'bg-primary' },
        { name: 'Data Structures', value: 15, color: 'bg-secondary' },
        { name: 'Algorithm Design', value: 10, color: 'bg-accent' },
      ]
    }
    if (currentPersona === 'bob') {
      return [
        { name: 'Financial Analysis', value: 90, color: 'bg-primary' },
        { name: 'Market Assessment', value: 85, color: 'bg-secondary' },
        { name: 'Policy Evaluation', value: 80, color: 'bg-accent' },
      ]
    }
    if (currentPersona === 'charles') {
      return [
        { name: 'Financial Statements', value: 75, color: 'bg-primary' },
        { name: 'Cost Accounting', value: 60, color: 'bg-secondary' },
        { name: 'Managerial Accounting', value: 50, color: 'bg-accent' },
      ]
    }
    return [
      { name: 'Financial Modeling', value: 85, color: 'bg-primary' },
      { name: 'Supply Chain Mgmt', value: 72, color: 'bg-secondary' },
      { name: 'Data Visualization', value: 40, color: 'bg-accent' },
    ]
  }

  const getPersonaRecommendations = () => {
    if (currentPersona === 'alice') {
      return [
        {
          icon: 'play_circle',
          badge: 'Video Lesson',
          badgeColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400',
          iconColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 group-hover:bg-red-600',
          borderColor: 'border-red-200/70 dark:border-red-700/40 hover:border-red-500/60',
          title: 'Video: Python Loops Explained',
          meta: '15 min video',
        },
        {
          icon: 'code',
          badge: 'Hands-On',
          badgeColor: 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
          iconColor: 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 group-hover:bg-indigo-600',
          borderColor: 'border-indigo-200/70 dark:border-indigo-700/40 hover:border-indigo-500/60',
          title: 'Coding Challenge: FizzBuzz',
          meta: '30 min activity',
        },
        {
          icon: 'play_circle',
          badge: 'Video Lesson',
          badgeColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400',
          iconColor: 'bg-red-50 dark:bg-red-900/30 text-red-600 group-hover:bg-red-600',
          borderColor: 'border-red-200/70 dark:border-red-700/40 hover:border-red-500/60',
          title: 'Video: Understanding Functions',
          meta: '22 min video',
        },
      ]
    }
    if (currentPersona === 'bob') {
      return [
        {
          icon: 'auto_stories',
          badge: 'Deep Dive',
          badgeColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary',
          iconColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary group-hover:bg-secondary',
          borderColor: 'border-amber-200/70 dark:border-amber-700/40 hover:border-secondary/60',
          title: 'Reading: Capital Markets Case Study',
          meta: '25 page PDF',
        },
        {
          icon: 'forum',
          badge: 'AI Discussion',
          badgeColor: 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
          iconColor: 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 group-hover:bg-purple-600',
          borderColor: 'border-purple-200/70 dark:border-purple-700/40 hover:border-purple-500/60',
          title: 'Discuss: Detroit Economic Revival',
          meta: 'Interactive chat',
        },
        {
          icon: 'auto_stories',
          badge: 'Deep Dive',
          badgeColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary',
          iconColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary group-hover:bg-secondary',
          borderColor: 'border-amber-200/70 dark:border-amber-700/40 hover:border-secondary/60',
          title: 'Real Estate Finance Analysis',
          meta: '18 page PDF',
        },
      ]
    }
    if (currentPersona === 'charles') {
      return [
        {
          icon: 'style',
          badge: 'Flashcards',
          badgeColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary',
          iconColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary group-hover:bg-primary',
          borderColor: 'border-emerald-200/70 dark:border-emerald-700/40 hover:border-primary/60',
          title: 'Review: Journal Entry Rules',
          meta: '50 cards',
        },
        {
          icon: 'quiz',
          badge: 'Quick Quiz',
          badgeColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent',
          iconColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent group-hover:bg-accent',
          borderColor: 'border-orange-200/70 dark:border-orange-700/40 hover:border-accent/60',
          title: 'Quiz: Revenue Recognition',
          meta: '10 questions',
        },
        {
          icon: 'style',
          badge: 'Flashcards',
          badgeColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary',
          iconColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary group-hover:bg-primary',
          borderColor: 'border-emerald-200/70 dark:border-emerald-700/40 hover:border-primary/60',
          title: 'Review: Financial Ratios',
          meta: '30 cards',
        },
      ]
    }
    return [
      {
        icon: 'monitoring',
        badge: 'Tech Interest',
        badgeColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary',
        iconColor: 'bg-emerald-50 dark:bg-emerald-900/30 text-primary group-hover:bg-primary',
        borderColor: 'border-emerald-200/70 dark:border-emerald-700/40 hover:border-primary/60',
        title: 'Advanced Financial Modeling Activity',
        meta: '45 min activity',
      },
      {
        icon: 'auto_stories',
        badge: 'Deep Dive',
        badgeColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary',
        iconColor: 'bg-amber-50 dark:bg-amber-900/30 text-secondary group-hover:bg-secondary',
        borderColor: 'border-amber-200/70 dark:border-amber-700/40 hover:border-secondary/60',
        title: 'Sustainability in Supply Chain - Required Reading',
        meta: '12 page PDF',
      },
      {
        icon: 'play_circle',
        badge: 'Video Lesson',
        badgeColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent',
        iconColor: 'bg-orange-50 dark:bg-orange-900/30 text-accent group-hover:bg-accent',
        borderColor: 'border-orange-200/70 dark:border-orange-700/40 hover:border-accent/60',
        title: 'Foundations of Quantitative Analysis',
        meta: '18 min video',
      },
    ]
  }

  const { progress, percentile } = getPersonaProgress()
  const skills = getPersonaSkills()
  const recommendations = getPersonaRecommendations()

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
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white font-display">
                Welcome back, {getPersonaGreeting()}.
              </h1>
              {persona && (
                <p className="text-sm text-slate-600 dark:text-slate-300 font-semibold">
                  {persona.major} · {persona.courseTitle}
                </p>
              )}
              <p className="text-slate-500 dark:text-slate-400 font-medium">
                Your personalized learning path is <span className="text-primary font-bold">{progress}% complete</span>.
                You're ahead of {percentile}% of your cohort.
              </p>
            </div>
            <div className="flex gap-3">
              <button className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light transition-all shadow-md shadow-primary/20">
                Resume Learning
              </button>
              <button className="rounded-xl border-2 border-primary/30 px-5 py-2.5 text-sm font-bold text-primary hover:bg-primary/10 dark:hover:bg-primary/20 transition-colors">
                View Full Path
              </button>
            </div>
          </div>
          <div className="mt-8 space-y-3">
            <div className="flex justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Core Fundamentals</span>
              <span>Advanced Specialization</span>
            </div>
            <div className="relative h-4 w-full overflow-hidden rounded-full bg-stone-200/80 dark:bg-slate-800">
              <div
                className="absolute h-full rounded-full bg-gradient-to-r from-primary to-primary-light shadow-lg shadow-primary/30"
                style={{ width: `${progress}%` }}
              />
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
              {recommendations.map((rec, index) => (
                <div
                  key={index}
                  className={`group flex flex-col rounded-2xl bg-white/95 dark:bg-slate-900/95 border-2 p-4 shadow-soft transition-all duration-300 hover:shadow-xl ${rec.borderColor}`}
                >
                  <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg ${rec.iconColor} group-hover:text-white transition-colors`}>
                    <span className="material-symbols-outlined">{rec.icon}</span>
                  </div>
                  <span className={`mb-2 inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${rec.badgeColor}`}>
                    {rec.badge}
                  </span>
                  <h3 className="mb-4 text-sm font-bold text-stone-900 dark:text-white leading-snug font-display">
                    {rec.title}
                  </h3>
                  <div className="mt-auto flex items-center justify-between">
                    <span className="text-xs text-stone-400">{rec.meta}</span>
                    <span className="material-symbols-outlined text-stone-300 group-hover:text-primary">arrow_forward</span>
                  </div>
                </div>
              ))}
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
                  {skills.map((skill, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-wider">
                        <span>{skill.name}</span>
                        <span className="text-primary">{skill.value}%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                        <div className={`h-full rounded-full ${skill.color}`} style={{ width: `${skill.value}%` }} />
                      </div>
                    </div>
                  ))}
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
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">
                    {currentPersona === 'alice' ? 'Problem Set 2 Due' : currentPersona === 'bob' ? 'Case Study Analysis' : currentPersona === 'charles' ? 'Midterm Exam Prep' : 'Midterm Project Submission'}
                  </h4>
                  <p className="text-xs text-slate-500">Due in 3 days · {persona?.courseTitle.slice(0, 20) || 'Econ 301'}</p>
                </div>
              </div>
              <div className="flex gap-4 rounded-xl border-l-4 border-primary bg-white dark:bg-slate-900 p-4 shadow-sm border-2 border-emerald-100 dark:border-emerald-900/40">
                <div className="flex-1 space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-primary">Assessment</p>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">
                    {currentPersona === 'alice' ? 'Quiz: Python Basics' : currentPersona === 'bob' ? 'Quiz: Capital Markets' : currentPersona === 'charles' ? 'Quiz: Journal Entries' : 'Quiz: Macroeconomics'}
                  </h4>
                  <p className="text-xs text-slate-500">Friday, Oct 6 · 10:00 AM</p>
                </div>
              </div>
              <div className="flex gap-4 rounded-xl border-l-4 border-slate-300 bg-white dark:bg-slate-900 p-4 shadow-sm border-2 border-slate-200 dark:border-slate-700">
                <div className="flex-1 space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Study Reminder</p>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight font-display">
                    {currentPersona === 'alice' ? 'Practice Coding Exercises' : currentPersona === 'bob' ? 'Review Detroit Case Study' : currentPersona === 'charles' ? 'Flashcard Review Session' : 'Review Case Study 4'}
                  </h4>
                  <p className="text-xs text-slate-500">Personal Goal</p>
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
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300 font-medium">
                {currentPersona === 'alice' && 'Watch the video on loops before attempting the next problem set. Visual learning will help you grasp the concepts faster.'}
                {currentPersona === 'bob' && 'The Detroit case study relates closely to your current module. Spend extra time on the policy analysis section.'}
                {currentPersona === 'charles' && 'Based on your study pace, you can complete 3 more modules this week. Focus on flashcard reviews for maximum retention.'}
                {currentPersona === 'demo' && 'Based on your recent scores, focusing on "Exchange Rate Theory" could improve your upcoming quiz grade by ~15%.'}
              </p>
              <button className="mt-4 w-full rounded-xl bg-white dark:bg-slate-900 border-2 border-emerald-200 dark:border-emerald-800 py-2.5 text-xs font-bold text-primary hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-all shadow-sm">Add to Study Plan</button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
