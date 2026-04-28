export type HomeRoadmapStatus = 'completed' | 'current' | 'upcoming'

export type HomeRoadmapConcept = {
  id: string
  name: string
  status: HomeRoadmapStatus
  description?: string
}

export type HomeRoadmapOutcome = {
  id: string
  title: string
  status: HomeRoadmapStatus
  subtext?: string
  concepts?: HomeRoadmapConcept[]
}
