const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type Lesson = {
  lesson_id: string
  title: string
  concepts: { name: string; description: string }[]
  chunk_ids: string[]
  prerequisites: string[]
}

export type RoadmapResponse = {
  course: string
  lesson_count: number
  lessons: Lesson[]
}

export async function fetchRoadmap(): Promise<RoadmapResponse> {
  const res = await fetch(`${API_URL}/roadmap`)
  if (!res.ok) {
    throw new Error(`Failed to fetch roadmap: ${res.status}`)
  }
  return res.json()
}
