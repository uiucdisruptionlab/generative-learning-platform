import { useState } from 'react'
import AppLayout from '../components/AppLayout'

export default function MKTG440SEOPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="SEO Basics"
      description="Master search engine optimization and content discovery."
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-48 min-w-0">
        <div className="space-y-8">
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              What is SEO?
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Search Engine Optimization (SEO) is the practice of optimizing your content to appear higher in search
              engine results. It's about making your website more discoverable when people search for topics related to
              your business.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              Why this matters to you
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Over 90% of online experiences begin with a search engine. If your content doesn't appear in the first
              page of results, you're missing out on potential customers. Good SEO is the difference between being found
              or being invisible online.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4">
              Key SEO Components
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                <span className="material-symbols-outlined text-primary text-2xl mb-2">search</span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Keywords</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Words and phrases people search for to find content like yours.
                </p>
              </div>
              <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-4 border border-blue-200/60 dark:border-blue-700/40">
                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-2xl mb-2">
                  article
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Content Quality</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Well-written, relevant content that answers user questions.
                </p>
              </div>
              <div className="rounded-xl bg-purple-50 dark:bg-purple-900/20 p-4 border border-purple-200/60 dark:border-purple-700/40">
                <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-2xl mb-2">
                  link
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Backlinks</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Links from other reputable websites pointing to yours.
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 overflow-hidden border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <div className="h-24 bg-amber-100 dark:bg-amber-900/30" />
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
                Real Example: Local Coffee Shop
              </h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-6">
                A local coffee shop wanted to attract more customers. By optimizing their website with keywords like
                "best coffee in [city name]" and "artisan coffee shop near me," they improved their ranking from page 5
                to page 1 of Google results. Within 3 months, their foot traffic increased by{' '}
                <strong className="text-slate-900 dark:text-white">40%</strong>.
              </p>
              <div className="flex flex-wrap items-center gap-2 text-lg">
                <span className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-bold text-white">
                  Keyword Research
                </span>
                <span className="text-slate-500">+</span>
                <span className="inline-flex items-center rounded-full bg-slate-200 dark:bg-slate-600 px-4 py-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                  Quality Content
                </span>
                <span className="text-slate-500">=</span>
                <span className="inline-flex items-center rounded-full bg-primary-light px-4 py-2 text-sm font-bold text-white">
                  Higher Rankings
                </span>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-emerald-50 dark:from-amber-950/30 dark:to-emerald-950/20 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">edit</span>
              Try it yourself
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              Imagine you're launching a new fitness app. Think about:
            </p>
            <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 mb-4 space-y-1">
              <li>What keywords would your target users search for?</li>
              <li>What questions do beginners ask about fitness?</li>
              <li>How can you create content that answers those questions?</li>
            </ul>
            <p className="text-slate-600 dark:text-slate-300 pb-2">
              Need help brainstorming SEO strategies? Ask in the chat below!
            </p>
          </section>
          <div aria-hidden="true" className="shrink-0" style={{ height: '100px' }} />
        </div>

        <div
          className={`fixed bottom-0 right-0 z-20 border-t-2 border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md px-4 sm:px-6 py-3 sm:py-4 transition-[left] duration-300 ${
            sidebarOpen ? 'left-72' : 'left-0'
          }`}
        >
          <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-3 min-w-0 overflow-hidden">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 min-w-0 px-4 py-2.5 sm:py-3 rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 focus:border-primary focus:outline-none text-sm"
            />
            <button
              type="button"
              className="rounded-xl bg-primary px-4 sm:px-6 py-2.5 sm:py-3 text-sm font-bold text-white hover:bg-primary-light transition-colors whitespace-nowrap"
            >
              Ask
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
