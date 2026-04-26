export type HomeRoadmapOutcome = {
  id: string
  title: string
  status: 'completed' | 'current' | 'upcoming'
  subtext?: string
}
