import { createContext, useContext, useState, ReactNode } from 'react'
import { PERSONAS, DEFAULT_PERSONA } from '../data/personas'

type PersonaContextType = {
  currentPersona: string
  setCurrentPersona: (personaId: string) => void
  persona: typeof PERSONAS[keyof typeof PERSONAS] | null
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined)

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [currentPersona, setCurrentPersona] = useState(DEFAULT_PERSONA)

  const persona = currentPersona !== 'demo' ? PERSONAS[currentPersona] : null

  return (
    <PersonaContext.Provider value={{ currentPersona, setCurrentPersona, persona }}>
      {children}
    </PersonaContext.Provider>
  )
}

export function usePersona() {
  const context = useContext(PersonaContext)
  if (context === undefined) {
    throw new Error('usePersona must be used within a PersonaProvider')
  }
  return context
}
