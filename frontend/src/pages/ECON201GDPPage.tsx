import { useState } from 'react'
import AppLayout from '../components/AppLayout'

export default function ECON201GDPPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="GDP and National Income"
      description="Understanding how we measure economic output and growth."
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-48 min-w-0">
        <div className="space-y-8">
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              What is GDP?
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Gross Domestic Product (GDP) is the total monetary value of all goods and services produced within a
              country's borders in a specific time period. Think of it as a report card for the economy - it tells us
              whether the economy is growing, shrinking, or staying the same.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              Why this matters to you
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              GDP affects your daily life more than you might think. When GDP grows, there are typically more jobs,
              higher wages, and better business opportunities. When GDP shrinks, unemployment rises and economic
              opportunities decrease. Understanding GDP helps you make sense of economic news and its impact on your career
              and finances.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4">
              Components of GDP
            </h3>
            <div className="flex flex-wrap items-center gap-2 text-lg mb-4">
              <span className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-bold text-white">
                Consumption (C)
              </span>
              <span className="text-slate-500">+</span>
              <span className="inline-flex items-center rounded-full bg-blue-500 px-4 py-2 text-sm font-bold text-white">
                Investment (I)
              </span>
              <span className="text-slate-500">+</span>
              <span className="inline-flex items-center rounded-full bg-purple-500 px-4 py-2 text-sm font-bold text-white">
                Government (G)
              </span>
              <span className="text-slate-500">+</span>
              <span className="inline-flex items-center rounded-full bg-amber-500 px-4 py-2 text-sm font-bold text-white">
                Net Exports (X-M)
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                <span className="material-symbols-outlined text-primary text-2xl mb-2">shopping_cart</span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Consumption</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Household spending on goods and services - the largest component, typically 60-70% of GDP.
                </p>
              </div>
              <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-4 border border-blue-200/60 dark:border-blue-700/40">
                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-2xl mb-2">
                  business
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Investment</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Business spending on equipment, buildings, and inventory.
                </p>
              </div>
              <div className="rounded-xl bg-purple-50 dark:bg-purple-900/20 p-4 border border-purple-200/60 dark:border-purple-700/40">
                <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-2xl mb-2">
                  account_balance
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Government Spending</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Government purchases of goods and services, infrastructure, defense, etc.
                </p>
              </div>
              <div className="rounded-xl bg-amber-50 dark:bg-amber-900/20 p-4 border border-amber-200/60 dark:border-amber-700/40">
                <span className="material-symbols-outlined text-amber-600 dark:text-amber-400 text-2xl mb-2">
                  public
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Net Exports</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Value of exports minus imports (can be positive or negative).
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 overflow-hidden border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <div className="h-24 bg-emerald-100 dark:bg-emerald-900/30" />
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
                Real Example: U.S. GDP in 2023
              </h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-4">
                In 2023, the United States had a GDP of approximately{' '}
                <strong className="text-slate-900 dark:text-white">$27 trillion</strong>. Here's the breakdown:
              </p>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-32 text-sm font-semibold text-slate-700 dark:text-slate-300">Consumption:</div>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                    <div className="bg-primary h-full flex items-center justify-end pr-2" style={{ width: '68%' }}>
                      <span className="text-xs font-bold text-white">68%</span>
                    </div>
                  </div>
                  <div className="w-24 text-sm text-slate-600 dark:text-slate-400">$18.4T</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32 text-sm font-semibold text-slate-700 dark:text-slate-300">Investment:</div>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                    <div className="bg-blue-500 h-full flex items-center justify-end pr-2" style={{ width: '18%' }}>
                      <span className="text-xs font-bold text-white">18%</span>
                    </div>
                  </div>
                  <div className="w-24 text-sm text-slate-600 dark:text-slate-400">$4.9T</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32 text-sm font-semibold text-slate-700 dark:text-slate-300">Government:</div>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                    <div className="bg-purple-500 h-full flex items-center justify-end pr-2" style={{ width: '17%' }}>
                      <span className="text-xs font-bold text-white">17%</span>
                    </div>
                  </div>
                  <div className="w-24 text-sm text-slate-600 dark:text-slate-400">$4.6T</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32 text-sm font-semibold text-slate-700 dark:text-slate-300">Net Exports:</div>
                  <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                    <div className="bg-red-500 h-full flex items-center justify-end pr-2" style={{ width: '3%' }}>
                      <span className="text-xs font-bold text-white">-3%</span>
                    </div>
                  </div>
                  <div className="w-24 text-sm text-slate-600 dark:text-slate-400">-$0.8T</div>
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
              A small island nation has the following economic data for the year:
            </p>
            <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 mb-4 space-y-1">
              <li>Household consumption: $500 million</li>
              <li>Business investment: $100 million</li>
              <li>Government spending: $150 million</li>
              <li>Exports: $75 million</li>
              <li>Imports: $125 million</li>
            </ul>
            <p className="text-slate-600 dark:text-slate-300 pb-2">
              What is the country's GDP? Use the chat below to check your calculation!
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
