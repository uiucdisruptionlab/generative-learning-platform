const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type Lesson = {
  lesson_id: string
  title: string
  prerequisites: string[]
}

export type RoadmapResponse = {
  course_id: string
  lessons: Lesson[]
}

export async function fetchRoadmap(courseId: string): Promise<RoadmapResponse> {
  const res = await fetch(`${API_URL}/roadmap/course/${courseId}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch roadmap: ${res.status}`)
  }
  return res.json()
}
