import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'

export default function IncomeStatementPage() {
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="The Income Statement"
      description="Revenue, expenses, and net income – the basic formula."
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-48 min-w-0">
        {/* Main content */}
        <div className="space-y-8">
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              What is an Income Statement?
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Think of it like a highlight reel for a business — it shows everything that happened financially over a
              period of time. Revenue came in, costs went out, and what's left is the profit (or loss).
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              Why this matters to you
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Whether you're analyzing a company for media, advising on brand strategy, or managing a small team's
              budget, understanding income statements helps you see if a business is actually profitable.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4">
              The Basic Formula
            </h3>
            <div className="flex flex-wrap items-center gap-2 text-lg">
              <span className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-bold text-white">
                Revenue
              </span>
              <span className="text-slate-500">−</span>
              <span className="inline-flex items-center rounded-full bg-slate-200 dark:bg-slate-600 px-4 py-2 text-sm font-bold text-slate-700 dark:text-slate-200">
                Expenses
              </span>
              <span className="text-slate-500">=</span>
              <span className="inline-flex items-center rounded-full bg-primary-light px-4 py-2 text-sm font-bold text-white">
                Net Income
              </span>
            </div>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 overflow-hidden border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <div className="h-24 bg-red-100 dark:bg-red-900/30" />
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
                Real Example: Nike's 2023 Results
              </h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-6">
                In 2023, Nike reported <strong className="text-slate-900 dark:text-white">$51.2 billion</strong> in
                revenue. But after subtracting the cost of making their products, paying their employees, and running
                their operations, their net income was{' '}
                <strong className="text-slate-900 dark:text-white">$5.1 billion</strong>. The income statement is the
                document that walks you through how you get from one number to the other — showing exactly where the money
                went.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                  <span className="material-symbols-outlined text-primary text-2xl mb-2">payments</span>
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Revenue</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    Total money earned from selling products.
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4 border border-slate-200 dark:border-slate-600">
                  <span className="material-symbols-outlined text-slate-600 dark:text-slate-400 text-2xl mb-2">
                    description
                  </span>
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Expenses</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    All costs incurred to generate that revenue.
                  </p>
                </div>
                <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                  <span className="material-symbols-outlined text-primary text-2xl mb-2">bar_chart</span>
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Net Income</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    What's left after all expenses — the profit.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-emerald-50 dark:from-amber-950/30 dark:to-emerald-950/20 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">edit</span>
              Try it yourself
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              Imagine a coffee shop makes <strong className="text-slate-900 dark:text-white">$200,000</strong> in revenue
              this year. Their costs include:
            </p>
            <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 mb-4 space-y-1">
              <li>Coffee beans and supplies: $60,000</li>
              <li>Staff wages: $80,000</li>
              <li>Rent and utilities: $30,000</li>
            </ul>
            <p className="text-slate-600 dark:text-slate-300 pb-2">
              What's their net income? Ask a question in the chat below to check your answer.
            </p>
          </section>
          {/* Spacer to ensure content clears the fixed chat bar when scrolling */}
          <div aria-hidden="true" className="shrink-0" style={{ height: '100px' }} />
        </div>

        {/* Bottom bar - aligned with main content when sidebar open */}
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
            <div className="flex gap-2 shrink-0 flex-wrap">
              <button
                type="button"
                className="rounded-xl bg-primary px-4 sm:px-6 py-2.5 sm:py-3 text-sm font-bold text-white hover:bg-primary-light transition-colors whitespace-nowrap"
              >
                Ask
              </button>
              <button
                type="button"
                onClick={() => navigate('/roadmap')}
                className="rounded-xl border-2 border-primary/30 px-4 sm:px-5 py-2.5 sm:py-3 text-sm font-bold text-primary hover:bg-primary/10 dark:hover:bg-primary/20 transition-colors whitespace-nowrap"
              >
                I'm done for today
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
