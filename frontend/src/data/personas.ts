export type LearningPreference = 'videos' | 'reading' | 'flashcards' | 'hands-on' | 'ai-interaction' | 'quizzes'

export type Persona = {
  id: string
  name: string
  major: string
  courseTitle: string
  courseUrl: string
  hoursPerWeek: number
  learningPreferences: LearningPreference[]
  learningStyle: string
  experienceLevel: 'beginner' | 'intermediate' | 'advanced'
  primaryRoadmapPath: string
}

export const PERSONAS: Record<string, Persona> = {
  alice: {
    id: 'alice',
    name: 'Alice',
    major: 'Finance & Data Science',
    courseTitle: 'Introduction to Computer Science and Programming in Python',
    courseUrl: 'https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/',
    hoursPerWeek: 5,
    learningPreferences: ['videos', 'hands-on'],
    learningStyle: 'Prefers video lectures and hands-on coding problems. Not very familiar with programming yet.',
    experienceLevel: 'beginner',
    primaryRoadmapPath: '/roadmap/python',
  },
  bob: {
    id: 'bob',
    name: 'Bob',
    major: 'Business',
    courseTitle: 'Financing Economic Development',
    courseUrl: 'https://ocw.mit.edu/courses/11-437-financing-economic-development-fall-2016/',
    hoursPerWeek: 2,
    learningPreferences: ['reading', 'ai-interaction'],
    learningStyle: 'Enjoys reading detailed materials and discussing topics with AI using lots of examples. Very familiar with the subject matter.',
    experienceLevel: 'advanced',
    primaryRoadmapPath: '/roadmap/financing',
  },
  charles: {
    id: 'charles',
    name: 'Charles',
    major: 'Accounting',
    courseTitle: 'Introduction to Financial and Managerial Accounting',
    courseUrl: 'https://ocw.mit.edu/courses/15-501-introduction-to-financial-and-managerial-accounting-spring-2004/',
    hoursPerWeek: 10,
    learningPreferences: ['flashcards', 'quizzes'],
    learningStyle: 'Loves flashcard reviews and knowledge-testing questions. Can dedicate significant time to studying.',
    experienceLevel: 'intermediate',
    primaryRoadmapPath: '/roadmap/accounting',
  },
}

export const DEFAULT_PERSONA = 'demo'

const DEMO_SIDEBAR_AVATAR =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuDs46P0CZ3XO6IpxwKmlWOzkVVgpzXbgHshy0mB95PNbmEuNjREXUdGTy9uWs4yL3WiG3k00SqntZWP9ixeKoRrYw5KHge_gn69LU_absQEGK1VHQV2U2Hm91HQgAvIEcTdkchtjKtU3U0fEOjxezLIcdu7x_L7-Tz20vYYx_xU6J42r9a2hhztQsm447XonCJkerJtP3lzUzSUoJoLLeU1LObC2wSaNzunidTHSlUSIJ6zNtLTVDYumNRFEUtqAn65QR-AmQ4b9qsw'

/** Sidebar footer avatar + IDs keyed to PersonaToggle options. */
const PERSONA_SIDEBAR: Record<string, { studentId: string; avatarUrl: string }> = {
  alice: {
    studentId: '441892',
    avatarUrl:
      'https://ui-avatars.com/api/?name=Alice&size=128&background=287D3C&color=FFFFFF&bold=true',
  },
  bob: {
    studentId: '773205',
    avatarUrl:
      'https://ui-avatars.com/api/?name=Bob&size=128&background=CC5500&color=FFFFFF&bold=true',
  },
  charles: {
    studentId: '991034',
    avatarUrl:
      'https://ui-avatars.com/api/?name=Charles&size=128&background=2C5926&color=FFFFFF&bold=true',
  },
}

export type SidebarProfileDisplay = {
  displayName: string
  studentId: string
  avatarUrl: string
}

export function getSidebarProfile(personaId: string): SidebarProfileDisplay {
  if (personaId === 'demo') {
    return {
      displayName: 'Alex Johnson',
      studentId: '882104',
      avatarUrl: DEMO_SIDEBAR_AVATAR,
    }
  }
  const p = PERSONAS[personaId]
  const sidebar = PERSONA_SIDEBAR[personaId]
  if (p && sidebar) {
    return {
      displayName: p.name,
      studentId: sidebar.studentId,
      avatarUrl: sidebar.avatarUrl,
    }
  }
  return {
    displayName: 'Alex Johnson',
    studentId: '882104',
    avatarUrl: DEMO_SIDEBAR_AVATAR,
  }
}
