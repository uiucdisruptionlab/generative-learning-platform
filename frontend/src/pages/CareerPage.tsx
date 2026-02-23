import { useState } from 'react'
import AppLayout from '../components/AppLayout'

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Career Hub"
      description="Bridging the gap between academic excellence and professional success."
    >
      <div className="dashboard-content w-full max-w-[1440px] mx-auto min-w-0 px-4 py-6 sm:px-6 lg:px-12 lg:py-12">
        <div className="flex flex-col gap-8 min-w-0 w-full max-w-full">
          {/* Row 1: Professional Profile + Recommended Materials side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 min-w-0">
            <section className="bg-white/95 dark:bg-slate-900/95 rounded-xl p-6 shadow-sm border-2 border-emerald-200/70 dark:border-emerald-700/40 min-w-0 bg-gradient-to-br from-white via-emerald-50/20 to-white dark:from-slate-900 dark:via-emerald-950/10 dark:to-slate-900">
              <div className="flex items-center gap-4 mb-4 min-w-0">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-forest/15 to-forest/5 rounded-full shrink-0 ring-1 ring-forest/20">
                  <span className="material-symbols-outlined text-2xl text-forest">psychology</span>
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Professional Profile</h3>
                  <p className="text-xs font-semibold uppercase tracking-wider text-forest">AI-Generated Value Prop</p>
                </div>
              </div>
              <div className="bg-[#ecf3ea] dark:bg-forest/10 rounded-lg p-4 border-l-4 border-primary dark:border-forest/30 min-w-0">
                <p className="text-slate-700 dark:text-slate-300 italic leading-relaxed text-sm break-words [overflow-wrap:anywhere]">
                  &quot;You are a data-driven problem solver with a strong foundation in CS 411 and a passion for Ethical AI frameworks. Your ability to synthesize complex algorithms into actionable business insights makes you an ideal candidate for strategic analyst roles.&quot;
                </p>
              </div>
              <button className="mt-4 w-full py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-bold rounded-lg transition-colors flex items-center justify-center gap-2">
                <span className="material-symbols-outlined text-sm">edit</span>
                Edit Profile
              </button>
            </section>
            <section className="bg-white/95 dark:bg-slate-900/95 rounded-xl p-6 shadow-sm border-2 border-emerald-200/70 dark:border-emerald-700/40 min-w-0 bg-gradient-to-br from-white via-emerald-50/20 to-white dark:from-slate-900 dark:via-emerald-950/10 dark:to-slate-900">
              <div className="flex items-center justify-between mb-4 min-w-0 flex-wrap gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Recommended Materials</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-warm-yellow/20 text-warm-yellow rounded uppercase">Based on Profile</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-0">
                <div className="group p-4 bg-gradient-to-br from-amber-50/50 to-white dark:from-slate-800/80 dark:to-slate-900/80 rounded-lg border-2 border-amber-200/60 dark:border-amber-700/30 hover:border-forest/50 transition-all min-w-0">
                  <div className="flex justify-between items-start mb-2">
                    <span className="px-2 py-0.5 bg-forest text-[10px] font-bold text-white rounded shrink-0">CS 411</span>
                    <span className="material-symbols-outlined text-slate-300 text-sm shrink-0">description</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Advanced Relational Design</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-3 break-words [overflow-wrap:anywhere] line-clamp-2">
                    Covers <span className="highlight-keyword">relational database design</span> principles and normal forms.
                  </p>
                  <button className="w-full py-2 bg-white dark:bg-slate-900 border-2 border-forest text-forest text-xs font-bold rounded hover:bg-forest hover:text-white transition-colors flex items-center justify-center gap-1">
                    View Resource <span className="material-symbols-outlined text-xs">open_in_new</span>
                  </button>
                </div>
                <div className="group p-4 bg-gradient-to-br from-amber-50/50 to-white dark:from-slate-800/80 dark:to-slate-900/80 rounded-lg border-2 border-amber-200/60 dark:border-amber-700/30 hover:border-forest/50 transition-all min-w-0">
                  <div className="flex justify-between items-start mb-2">
                    <span className="px-2 py-0.5 bg-forest text-[10px] font-bold text-white rounded shrink-0">PHIL 202</span>
                    <span className="material-symbols-outlined text-slate-300 text-sm shrink-0">picture_as_pdf</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 font-display">Algorithmic Bias Module</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-3 break-words [overflow-wrap:anywhere] line-clamp-2">
                    A deep dive into <span className="highlight-keyword">Ethical AI</span> frameworks and bias mitigation.
                  </p>
                  <button className="w-full py-2 bg-white dark:bg-slate-900 border-2 border-forest text-forest text-xs font-bold rounded hover:bg-forest hover:text-white transition-colors flex items-center justify-center gap-1">
                    View Resource <span className="material-symbols-outlined text-xs">open_in_new</span>
                  </button>
                </div>
              </div>
              <a href="#" className="mt-4 block text-center text-xs font-bold text-forest hover:underline">See More Course Insights</a>
            </section>
          </div>
          {/* Row 2: AI Resume Tailoring - full width (user said this stays bigger) */}
          <section className="bg-white/95 dark:bg-slate-900/95 rounded-xl shadow-sm border border-amber-200/70 dark:border-amber-700/40 overflow-hidden min-w-0 bg-gradient-to-br from-white via-amber-50/10 to-white dark:from-slate-900 dark:via-amber-950/5 dark:to-slate-900">
              <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-4 bg-slate-50/50 dark:bg-slate-800/50 min-w-0">
                <div className="min-w-0">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white truncate">AI Resume Tailoring</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Compare your resume against target roles</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-forest/15 to-forest/5 rounded-full shrink-0 ring-1 ring-forest/20">
                  <span className="size-2 rounded-full animate-pulse bg-burnt-orange" />
                  <span className="text-xs font-bold uppercase tracking-tighter text-forest whitespace-nowrap">AI Analysis Active</span>
                </div>
              </div>
              <div className="p-6">
                <div className="flex flex-col gap-6">
                  <div className="space-y-4 min-w-0 overflow-hidden">
                    <div>
                      <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Target Job Description</label>
                      <textarea className="w-full min-h-[200px] rounded-xl border-2 border-forest/20 dark:border-forest/30 text-sm focus:ring-forest focus:border-forest px-4 py-3 resize-y" placeholder="Paste job description here..." rows={12} />
                    </div>
                    <div className="border-2 border-dashed border-forest/30 dark:border-forest/40 rounded-xl min-h-[160px] p-8 flex flex-col items-center justify-center text-center hover:bg-forest/5 dark:hover:bg-forest/10 transition-colors cursor-pointer">
                      <span className="material-symbols-outlined text-slate-400 text-3xl mb-2">upload_file</span>
                      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Upload your current resume</p>
                      <p className="text-xs text-slate-400 mt-1">PDF or DOCX (Max 5MB)</p>
                    </div>
                    <button className="w-full py-3 bg-forest text-white font-bold rounded-lg shadow-lg shadow-forest/20 hover:bg-[#1e3d1a] transition-all flex items-center justify-center gap-2">
                      <span className="material-symbols-outlined text-sm">analytics</span>
                      Analyze & Tailor
                    </button>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-5 border-2 border-forest/20 dark:border-forest/30 min-w-0 overflow-hidden">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2 font-display">
                      <span className="material-symbols-outlined text-sm text-forest">auto_awesome</span>
                      Tailoring Suggestions
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      <div className="bg-white dark:bg-slate-900 p-3 rounded-lg border-2 border-amber-200/60 dark:border-amber-700/30 border-l-4 border-l-warm-yellow shadow-sm min-w-0">
                        <p className="text-xs font-bold text-slate-400 uppercase">Skill Match Found</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 mt-1 break-words [overflow-wrap:anywhere]">Add <span className="font-bold text-slate-900 dark:text-white">&quot;Relational Database Design&quot;</span> from your CS 411 project.</p>
                      </div>
                      <div className="bg-white dark:bg-slate-900 p-3 rounded-lg border-2 border-emerald-200/60 dark:border-emerald-700/30 border-l-4 border-l-forest shadow-sm min-w-0">
                        <p className="text-xs font-bold text-slate-400 uppercase">Experience Refinement</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 mt-1 break-words [overflow-wrap:anywhere]">Quantify impact: &quot;Improved member retention by 15% using <span className="font-bold">data-driven</span> analysis.&quot;</p>
                      </div>
                      <div className="bg-white dark:bg-slate-900 p-3 rounded-lg border-2 border-orange-200/60 dark:border-orange-700/30 border-l-4 border-l-burnt-orange shadow-sm min-w-0">
                        <p className="text-xs font-bold text-slate-400 uppercase">Missing Keyword</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 mt-1 break-words [overflow-wrap:anywhere]">Target role emphasizes <span className="font-bold text-slate-900 dark:text-white">&quot;Agile Methodology&quot;</span>. Ensure this is highlighted.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
          </section>

          {/* Row 3: Recommended Industry Primers - already 2 cols */}
          <section className="min-w-0 overflow-hidden">
              <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display">Recommended Industry Primers</h3>
                <a href="#" className="text-sm font-semibold text-forest hover:underline">Explore All Primers</a>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-0">
                <div className="group relative bg-white/95 dark:bg-slate-900/95 border-2 border-emerald-200/60 dark:border-emerald-700/40 rounded-xl p-5 hover:border-forest/80 hover:shadow-lg hover:shadow-forest/10 transition-all overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <span className="material-symbols-outlined text-6xl">payments</span>
                  </div>
                  <div className="relative z-10">
                    <div className="size-10 bg-forest/10 text-forest rounded-lg flex items-center justify-center mb-4">
                      <span className="material-symbols-outlined">account_balance</span>
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white mb-1">FinTech Ecosystem Overview</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 line-clamp-2">Understand the intersection of banking regulations and modern software infrastructure.</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-400 uppercase flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">schedule</span> 15 min read
                      </span>
                      <button className="text-sm font-bold flex items-center gap-1 text-forest group-hover:translate-x-1 transition-transform">
                        Start <span className="material-symbols-outlined text-xs font-bold">arrow_forward</span>
                      </button>
                    </div>
                  </div>
                </div>
                <div className="group relative bg-white/95 dark:bg-slate-900/95 border-2 border-amber-200/60 dark:border-amber-700/40 rounded-xl p-5 hover:border-forest/80 hover:shadow-lg hover:shadow-forest/10 transition-all overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <span className="material-symbols-outlined text-6xl">gavel</span>
                  </div>
                  <div className="relative z-10">
                    <div className="size-10 bg-warm-yellow/10 text-warm-yellow rounded-lg flex items-center justify-center mb-4">
                      <span className="material-symbols-outlined">balance</span>
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white mb-1 font-display">Ethical AI Frameworks</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 line-clamp-2">Learn industry standards for bias mitigation and algorithmic transparency in tech.</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-400 uppercase flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">schedule</span> 25 min read
                      </span>
                      <button className="text-sm font-bold flex items-center gap-1 text-forest group-hover:translate-x-1 transition-transform">
                        Start <span className="material-symbols-outlined text-xs font-bold">arrow_forward</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
          </section>
        </div>

        <footer className="mt-12 border-t border-primary/15 dark:border-primary/20 bg-white dark:bg-slate-900 py-6 lg:py-8 px-4 sm:px-6 lg:px-12">
          <div className="max-w-[1440px] mx-auto w-full flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="material-symbols-outlined text-sm">school</span>
              <span className="text-xs font-medium uppercase tracking-widest">UIUC Career Services Partnership</span>
            </div>
            <div className="flex gap-6">
              <a href="#" className="text-xs text-slate-400 hover:text-forest transition-colors">Privacy Policy</a>
              <a href="#" className="text-xs text-slate-400 hover:text-forest transition-colors">Terms of Use</a>
              <a href="#" className="text-xs text-slate-400 hover:text-forest transition-colors">Contact Support</a>
            </div>
          </div>
        </footer>
      </div>
    </AppLayout>
  )
}
