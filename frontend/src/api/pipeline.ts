import type { RoadmapResponse } from './roadmap'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type ConceptGraphConcept = {
  name: string
  description?: string | null
}

export type ConceptGraphRelationship = {
  from: string
  to: string
  type: string
}

export type ConceptGraphChunkLink = {
  chunk_id?: string
  lecture_id?: string
  chunk_order?: number
  concept_name?: string
}

export type ConceptGraphPayload = {
  lecture_id?: string
  concepts: ConceptGraphConcept[]
  relationships: ConceptGraphRelationship[]
  chunk_links: ConceptGraphChunkLink[]
}

export type PipelineIngestStats = {
  text_element_count: number
  total_chunks: number
  chunks_processed: number
  truncated: boolean
}

export type PipelineIngestResponse = {
  lecture_id: string
  source_filename: string
  chunk_count: number
  concept_count: number
  relationship_count: number
  /** Present when ingesting via POST /pipeline/ingest */
  ingest_stats?: PipelineIngestStats
  graph: ConceptGraphPayload
  roadmap: RoadmapResponse
}

export async function ingestPipelinePdf(
  file: File,
  options?: { refine?: boolean }
): Promise<PipelineIngestResponse> {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  if (options?.refine) params.set('refine', 'true')
  const qs = params.toString()
  const url = `${API_URL}/pipeline/ingest${qs ? `?${qs}` : ''}`
  const res = await fetch(url, { method: 'POST', body: form })
  if (!res.ok) {
    let message = await res.text()
    try {
      const parsed = JSON.parse(message) as { detail?: unknown }
      if (parsed.detail !== undefined) {
        message = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail)
      }
    } catch {
      /* keep raw text */
    }
    throw new Error(message || `Ingest failed (${res.status})`)
  }
  return res.json()
}
