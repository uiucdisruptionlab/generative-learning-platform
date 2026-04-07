import type { HomeRoadmapOutcome } from '../data/homeRoadmapPreview'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type LessonConcept = {
  name: string
  description: string
  importance_score?: number
}

export type Lesson = {
  lesson_id: string
  title: string
  summary?: string
  importance_score?: number
  concepts: LessonConcept[]
  chunk_ids: string[]
  lecture_ids?: string[]
  prerequisites: string[]
}

export type RoadmapResponse = {
  course: string
  lecture_id?: string
  lesson_count: number
  lessons: Lesson[]
}

export type FetchRoadmapParams = {
  course?: string
  lectureId?: string
  refine?: boolean
}

export async function fetchRoadmap(params: FetchRoadmapParams = {}): Promise<RoadmapResponse> {
  const search = new URLSearchParams()
  if (params.course) search.set('course', params.course)
  if (params.lectureId) search.set('lecture_id', params.lectureId)
  if (params.refine) search.set('refine', 'true')

  const url = `${API_URL}/roadmap${search.toString() ? `?${search.toString()}` : ''}`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Failed to fetch roadmap: ${res.status}`)
  }
  return res.json()
}

export function mapLessonsToOutcomes(lessons: Lesson[]): HomeRoadmapOutcome[] {
  return lessons.map((lesson, index) => {
    const topConcept = lesson.concepts[0]
    const summary = lesson.summary?.trim()
    const conceptDescription = topConcept?.description?.trim()
    return {
      id: lesson.lesson_id,
      title: lesson.title,
      status: index === 0 ? 'current' : 'upcoming',
      subtext: summary || conceptDescription || undefined,
    }
  })
}
