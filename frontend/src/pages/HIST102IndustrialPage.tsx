import { useState } from 'react'
import AppLayout from '../components/AppLayout'

export default function HIST102IndustrialPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="The Industrial Revolution"
      description="The transformation of society through industrialization."
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-48 min-w-0">
        <div className="space-y-8">
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              What was the Industrial Revolution?
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              The Industrial Revolution (roughly 1760-1840) was a period of massive technological, economic, and social
              change. It marked the shift from hand production to machine manufacturing, from rural agrarian societies to
              urban industrial ones.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              Why this matters to you
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              The Industrial Revolution shaped the modern world we live in today. It created the foundations for modern
              capitalism, urbanization, and technological progress. Understanding this period helps explain current
              economic systems, labor rights, and social structures.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4">
              Key Innovations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                <span className="material-symbols-outlined text-primary text-2xl mb-2">settings</span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Steam Engine</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Powered factories, trains, and ships - revolutionizing transportation and production.
                </p>
              </div>
              <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-4 border border-blue-200/60 dark:border-blue-700/40">
                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-2xl mb-2">
                  factory
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Factory System</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Centralized production replaced cottage industries and home-based work.
                </p>
              </div>
              <div className="rounded-xl bg-purple-50 dark:bg-purple-900/20 p-4 border border-purple-200/60 dark:border-purple-700/40">
                <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-2xl mb-2">
                  train
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Railroad Network</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Connected cities and enabled mass movement of goods and people.
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 overflow-hidden border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <div className="h-24 bg-slate-600 dark:bg-slate-700/30" />
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
                Real Example: Manchester, England
              </h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-6">
                Manchester transformed from a small market town of about{' '}
                <strong className="text-slate-900 dark:text-white">25,000</strong> people in 1772 to a major industrial
                city of over <strong className="text-slate-900 dark:text-white">300,000</strong> by 1850. It became known
                as "Cottonopolis" due to its massive cotton textile industry. However, this rapid growth came with
                significant challenges: overcrowded housing, pollution, poor sanitation, and harsh working conditions.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Positive Impacts</h4>
                  <ul className="text-xs text-slate-600 dark:text-slate-400 list-disc list-inside space-y-1">
                    <li>Increased production and wealth</li>
                    <li>New job opportunities</li>
                    <li>Technological advancement</li>
                  </ul>
                </div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4 border border-slate-200 dark:border-slate-600">
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Negative Impacts</h4>
                  <ul className="text-xs text-slate-600 dark:text-slate-400 list-disc list-inside space-y-1">
                    <li>Poor working conditions</li>
                    <li>Child labor exploitation</li>
                    <li>Environmental pollution</li>
                  </ul>
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
              Consider this scenario: You're a factory owner in 1830s England. Your competitors are adopting steam-powered
              machinery.
            </p>
            <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 mb-4 space-y-1">
              <li>What economic pressures would you face?</li>
              <li>How would adopting new technology affect your workers?</li>
              <li>What social responsibilities, if any, do you have?</li>
            </ul>
            <p className="text-slate-600 dark:text-slate-300 pb-2">
              Discuss the ethical dilemmas of industrialization in the chat below!
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
