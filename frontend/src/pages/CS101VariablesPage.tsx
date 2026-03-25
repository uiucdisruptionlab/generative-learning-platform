import { useState } from 'react'
import AppLayout from '../components/AppLayout'

export default function CS101VariablesPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Variables and Data Types"
      description="Learn how Python stores and uses different types of data."
    >
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-12 py-6 sm:py-8 pb-48 min-w-0">
        <div className="space-y-8">
          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              What are Variables?
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Think of variables as labeled containers that store information. In Python, you can store numbers, text,
              true/false values, and more. The variable name is the label, and the data inside is the value.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
              Why this matters to you
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              Every program you write will use variables. Whether you're building a game, analyzing data, or creating a
              website, understanding how to store and manipulate data is fundamental to programming.
            </p>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 border-2 border-emerald-200/80 dark:border-emerald-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-4">
              Common Data Types
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 p-4 border border-emerald-200/60 dark:border-emerald-700/40">
                <span className="material-symbols-outlined text-primary text-2xl mb-2">tag</span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Integers (int)</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                  Whole numbers without decimals.
                </p>
                <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">age = 25</code>
              </div>
              <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-4 border border-blue-200/60 dark:border-blue-700/40">
                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-2xl mb-2">
                  format_quote
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Strings (str)</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                  Text enclosed in quotes.
                </p>
                <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">name = "Alice"</code>
              </div>
              <div className="rounded-xl bg-purple-50 dark:bg-purple-900/20 p-4 border border-purple-200/60 dark:border-purple-700/40">
                <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-2xl mb-2">
                  toggle_on
                </span>
                <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">Booleans (bool)</h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                  True or False values.
                </p>
                <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">is_student = True</code>
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-white/90 dark:bg-slate-900/90 overflow-hidden border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <div className="h-24 bg-emerald-100 dark:bg-emerald-900/30" />
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-3">
                Real Example: Simple Calculator
              </h3>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-4">
                Let's see variables in action with a simple calculation:
              </p>
              <div className="rounded-xl bg-slate-900 dark:bg-slate-950 p-4 mb-4">
                <pre className="text-sm text-green-400 font-mono">
                  <code>{`price = 50.99
quantity = 3
total = price * quantity
print(f"Total: \${total}")  # Output: Total: $152.97`}</code>
                </pre>
              </div>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Here we stored numbers in variables, performed a calculation, and displayed the result. Python automatically
                figured out the data types based on what we stored.
              </p>
            </div>
          </section>

          <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-emerald-50 dark:from-amber-950/30 dark:to-emerald-950/20 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">edit</span>
              Try it yourself
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              Create three variables:
            </p>
            <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 mb-4 space-y-1">
              <li>A string variable called <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">greeting</code> with the value "Hello"</li>
              <li>An integer variable called <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">year</code> with the value 2024</li>
              <li>A boolean variable called <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">is_learning</code> with the value True</li>
            </ul>
            <p className="text-slate-600 dark:text-slate-300 pb-2">
              What would happen if you tried to add <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">greeting + year</code>? Ask in the chat below!
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
