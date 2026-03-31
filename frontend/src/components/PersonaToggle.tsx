import { useState } from 'react'
import { PERSONAS } from '../data/personas'

type PersonaToggleProps = {
  currentPersona: string
  onPersonaChange: (personaId: string) => void
}

export default function PersonaToggle({ currentPersona, onPersonaChange }: PersonaToggleProps) {
  const [isOpen, setIsOpen] = useState(false)

  const personas = [
    { id: 'demo', name: 'Demo', icon: 'play_circle' },
    { id: 'alice', name: 'Alice', icon: 'person' },
    { id: 'bob', name: 'Bob', icon: 'person' },
    { id: 'charles', name: 'Charles', icon: 'person' },
  ]

  const currentPersonaData = personas.find((p) => p.id === currentPersona) || personas[0]

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-900 border-2 border-primary/30 dark:border-primary/40 rounded-2xl shadow-lg hover:shadow-xl transition-all hover:border-primary/50 group"
        >
          <span className="material-symbols-outlined text-primary group-hover:scale-110 transition-transform">
            {currentPersonaData.icon}
          </span>
          <span className="text-sm font-bold text-slate-900 dark:text-white">
            {currentPersonaData.name}
          </span>
          <span
            className={`material-symbols-outlined text-slate-400 transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
          >
            expand_more
          </span>
        </button>

        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute bottom-full mb-2 right-0 w-64 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-2xl shadow-xl overflow-hidden z-50">
              <div className="p-4 bg-gradient-to-br from-primary/5 to-primary/10 dark:from-primary/10 dark:to-primary/20 border-b-2 border-primary/20">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">swap_horiz</span>
                  Switch Persona
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  View different student experiences
                </p>
              </div>
              <div className="p-2">
                {personas.map((persona) => {
                  const isActive = persona.id === currentPersona
                  const personaInfo = persona.id !== 'demo' ? PERSONAS[persona.id] : null

                  return (
                    <button
                      key={persona.id}
                      onClick={() => {
                        onPersonaChange(persona.id)
                        setIsOpen(false)
                      }}
                      className={`w-full flex items-start gap-3 p-3 rounded-xl transition-all ${
                        isActive
                          ? 'bg-primary/10 dark:bg-primary/20 border-2 border-primary/30'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800 border-2 border-transparent'
                      }`}
                    >
                      <div
                        className={`flex items-center justify-center size-10 rounded-full shrink-0 ${
                          isActive
                            ? 'bg-primary text-white'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                        }`}
                      >
                        <span className="material-symbols-outlined">{persona.icon}</span>
                      </div>
                      <div className="flex-1 text-left min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                            {persona.name}
                          </h4>
                          {isActive && (
                            <span className="material-symbols-outlined text-primary text-sm">
                              check_circle
                            </span>
                          )}
                        </div>
                        {personaInfo ? (
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {personaInfo.major} · {personaInfo.hoursPerWeek}h/week
                          </p>
                        ) : (
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            General showcase
                          </p>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
