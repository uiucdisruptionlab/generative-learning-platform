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

export const DEFAULT_PERSONA = 'charles'
