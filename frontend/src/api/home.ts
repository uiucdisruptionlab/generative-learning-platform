const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export { studentIdForPersona } from '../auth/studentIdentity'

export type StudentProfile = {
  id: string
  name: string
  academic_level?: string
  major_or_field?: string
  interests?: string[]
  weekly_hours?: number
  created_at?: string
  updated_at?: string
  learning_goals?: {
    primary_focus?: string
    target_course?: string
    course?: string
    [key: string]: unknown
  }
  preferred_formats?: string[]
  llm_profile?: {
    notes?: string
    learning_style_summary?: string
    subject_confidence?: string
    [key: string]: unknown
  }
}

export type RoadmapPosition = {
  student_id: string
  current_index: number
  updated_at?: string
}

export type RoadmapState = 'completed' | 'active' | 'locked'

export type GeneratedRoadmapConcept = {
  id?: string
  name?: string
  description?: string
  state?: RoadmapState
}

export type GeneratedRoadmapLesson = {
  lesson_id: string
  title: string
  summary?: string
  lecture_ids?: string[]
  state: RoadmapState
  concepts: GeneratedRoadmapConcept[]
}

export type GeneratedRoadmap = {
  student_id: string
  course_id: string
  current_index?: number
  node_ids: string[]
  /** Lecture-grouped, LLM-refined lessons (the primary roadmap unit). */
  lessons?: GeneratedRoadmapLesson[]
  /** Flat list of concepts (mirrors `node_ids`); kept for legacy consumers. */
  concepts?: GeneratedRoadmapConcept[]
}

export type CourseNode = {
  id: string
  title: string
  course_code?: string
  professor?: string
}

export type DueSrsRecord = {
  concept_id?: string
  node_id?: string
  next_review_at?: string
  [key: string]: unknown
}

export type DueSrsResponse = {
  student_id: string
  due: DueSrsRecord[]
  review_mode: boolean
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchHomeData(studentId: string): Promise<{
  student: StudentProfile
  roadmapPosition: RoadmapPosition
  roadmap: GeneratedRoadmap
  srsDue: DueSrsResponse
}> {
  const [student, roadmapPosition, roadmap, srsDue] = await Promise.all([
    getJson<StudentProfile>(`/student/${studentId}`),
    getJson<RoadmapPosition>(`/roadmap_position/${studentId}`),
    getJson<GeneratedRoadmap>(`/roadmap/${studentId}`),
    getJson<DueSrsResponse>(`/srs/due/${studentId}`),
  ])

  return { student, roadmapPosition, roadmap, srsDue }
}

export async function fetchStudentRoadmapData(studentId: string): Promise<{
  student: StudentProfile
  roadmapPosition: RoadmapPosition
  roadmap: GeneratedRoadmap
}> {
  const [student, roadmapPosition, roadmap] = await Promise.all([
    getJson<StudentProfile>(`/student/${studentId}`),
    getJson<RoadmapPosition>(`/roadmap_position/${studentId}`),
    getJson<GeneratedRoadmap>(`/roadmap/${studentId}`),
  ])
  return { student, roadmapPosition, roadmap }
}

export async function fetchCoursesData(studentId: string): Promise<{
  courses: CourseNode[]
  roadmap: GeneratedRoadmap
}> {
  const [coursesResponse, roadmap] = await Promise.all([
    getJson<{ courses: CourseNode[] }>(`/student/${studentId}/courses`),
    getJson<GeneratedRoadmap>(`/roadmap/${studentId}`),
  ])
  return { courses: coursesResponse.courses, roadmap }
}

export async function fetchStudent(studentId: string): Promise<StudentProfile> {
  return getJson<StudentProfile>(`/student/${studentId}`)
}
