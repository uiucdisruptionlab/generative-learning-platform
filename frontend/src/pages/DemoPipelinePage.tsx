import { useCallback, useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import LearningRoadmap from '../components/LearningRoadmap'
import { ingestPipelinePdf, type PipelineIngestResponse } from '../api/pipeline'
import { mapLessonsToOutcomes } from '../api/roadmap'

const PROCESS_STEPS = [
  { id: 'extract', label: 'Extracting text from the PDF' },
  { id: 'chunk', label: 'Chunking content for analysis' },
  { id: 'concepts', label: 'Extracting concepts (Bedrock) and relationships' },
  { id: 'neo4j', label: 'Writing nodes and edges to Neo4j' },
  { id: 'roadmap', label: 'Building roadmap from the graph' },
] as const

type Phase = 'idle' | 'processing' | 'done' | 'error'

export default function DemoPipelinePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [activeStep, setActiveStep] = useState(0)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PipelineIngestResponse | null>(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    if (phase !== 'processing') return
    setActiveStep(0)
    const id = window.setInterval(() => {
      setActiveStep((s) => Math.min(s + 1, PROCESS_STEPS.length - 1))
    }, 3200)
    return () => window.clearInterval(id)
  }, [phase])

  const onFile = useCallback((file: File | null) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please choose a PDF file.')
      return
    }
    setError(null)
    setSelectedFile(file)
    setResult(null)
    setPhase('idle')
  }, [])

  const runPipeline = useCallback(async () => {
    const file = selectedFile
    if (!file) {
      setError('Select a PDF first.')
      return
    }
    setPhase('processing')
    setError(null)
    setResult(null)
    try {
      const data = await ingestPipelinePdf(file, { refine: false })
      setResult(data)
      setPhase('done')
      setActiveStep(PROCESS_STEPS.length - 1)
    } catch (e) {
      setPhase('error')
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [selectedFile])

  const outcomes =
    result?.roadmap.lessons?.length ? mapLessonsToOutcomes(result.roadmap.lessons) : undefined

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="Upload → graph → roadmap"
      description="Demo: runs the backend PDF pipeline into Neo4j, then renders roadmap data from the graph."
    >
      <div className="max-w-3xl w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12 space-y-10">
        <section className="rounded-2xl border border-emerald-200/70 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-900/40 p-6 shadow-sm">
          <h2 className="text-lg font-bold font-display text-slate-900 dark:text-white mb-2">
            1. Upload a PDF
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
            The API uses Unstructured to read the file, chunks it, then runs{' '}
            <strong className="text-slate-700 dark:text-slate-300">one Bedrock call per chunk</strong> for concept
            extraction. Large PDFs can produce hundreds of chunks, so the server caps how many are processed (default{' '}
            <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">PIPELINE_MAX_CHUNKS=40</code> in{' '}
            <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">.env</code>; set to{' '}
            <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">none</code> for no cap — slow).
          </p>
          <div
            className={`rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragOver
                ? 'border-primary bg-primary/5'
                : 'border-slate-200 dark:border-slate-600 hover:border-primary/50'
            }`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              const f = e.dataTransfer.files?.[0]
              if (f) {
                onFile(f)
                const input = document.getElementById('demo-pipeline-file') as HTMLInputElement | null
                if (input) {
                  const dt = new DataTransfer()
                  dt.items.add(f)
                  input.files = dt.files
                }
              }
            }}
          >
            <input
              id="demo-pipeline-file"
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
            <span className="material-symbols-outlined text-4xl text-primary/80 mb-2">upload_file</span>
            <p className="text-slate-700 dark:text-slate-300 font-medium mb-3">
              {selectedFile ? selectedFile.name : 'Drag a PDF here or choose a file'}
            </p>
            <label
              htmlFor="demo-pipeline-file"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-light cursor-pointer shadow-md shadow-primary/20"
            >
              <span className="material-symbols-outlined text-lg">folder_open</span>
              Browse
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!selectedFile || phase === 'processing'}
              onClick={runPipeline}
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-bold text-white hover:opacity-95 disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            >
              {phase === 'processing' ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                  Processing…
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-lg">play_arrow</span>
                  Run pipeline
                </>
              )}
            </button>
            {phase === 'done' && (
              <span className="text-sm text-primary font-semibold self-center">Complete</span>
            )}
          </div>
          {error && (
            <div className="mt-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300 whitespace-pre-wrap">
              {error}
            </div>
          )}
        </section>

        {phase === 'processing' && (
          <section className="rounded-2xl border border-amber-200/80 dark:border-amber-900/40 bg-amber-50/50 dark:bg-slate-900/30 p-6">
            <h2 className="text-lg font-bold font-display text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary animate-pulse">hourglass_top</span>
              2. Extraction in progress
            </h2>
            <ol className="space-y-3">
              {PROCESS_STEPS.map((step, index) => {
                const status =
                  index < activeStep ? 'done' : index === activeStep ? 'active' : 'pending'
                return (
                  <li
                    key={step.id}
                    className={`flex items-start gap-3 rounded-xl px-3 py-2 border ${
                      status === 'active'
                        ? 'border-primary bg-primary/5'
                        : status === 'done'
                          ? 'border-emerald-200/80 dark:border-emerald-800/50 bg-white/60 dark:bg-slate-950/20'
                          : 'border-transparent opacity-60'
                    }`}
                  >
                    <span
                      className={`mt-0.5 material-symbols-outlined text-xl shrink-0 ${
                        status === 'active' ? 'text-primary animate-spin' : ''
                      }`}
                    >
                      {status === 'done'
                        ? 'check_circle'
                        : status === 'active'
                          ? 'progress_activity'
                          : 'radio_button_unchecked'}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        status === 'active' ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      {step.label}
                    </span>
                  </li>
                )
              })}
            </ol>
            <p className="text-xs text-slate-500 dark:text-slate-500 mt-4">
              Each chunk is a separate model call; without a chunk cap this can take a very long time on long PDFs.
            </p>
          </section>
        )}

        {phase === 'done' && result && (
          <>
            {result.ingest_stats?.truncated && (
              <div className="rounded-xl border border-amber-300/80 bg-amber-50 dark:bg-amber-950/30 px-4 py-3 text-sm text-amber-950 dark:text-amber-100">
                <strong>Roadmap used a subset of the PDF:</strong> processed{' '}
                {result.ingest_stats.chunks_processed} of {result.ingest_stats.total_chunks} chunks (Bedrock cap). Raise{' '}
                <code className="text-xs bg-white/60 dark:bg-black/20 px-1 rounded">PIPELINE_MAX_CHUNKS</code> in backend{' '}
                <code className="text-xs bg-white/60 dark:bg-black/20 px-1 rounded">.env</code> if you need more.
              </div>
            )}
            <section className="rounded-2xl border border-emerald-200/70 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-900/40 p-6 shadow-sm">
              <h2 className="text-lg font-bold font-display text-slate-900 dark:text-white mb-2">
                3. Neo4j subgraph (ingested)
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                Lecture id <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">{result.lecture_id}</code>
                {' · '}
                {result.chunk_count} chunks · {result.concept_count} concepts · {result.relationship_count} relationships
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">Concepts</h3>
                  <ul className="max-h-48 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-stone-50/80 dark:bg-slate-950/30 px-3 py-2 text-sm space-y-1">
                    {result.graph.concepts.map((c) => (
                      <li key={c.name} className="text-slate-800 dark:text-slate-200">
                        <span className="font-semibold">{c.name}</span>
                        {c.description ? (
                          <span className="text-slate-500 dark:text-slate-400"> — {c.description}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">Relationships</h3>
                  <ul className="max-h-48 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-stone-50/80 dark:bg-slate-950/30 px-3 py-2 text-sm space-y-1 font-mono text-xs">
                    {result.graph.relationships.length === 0 ? (
                      <li className="text-slate-500">No edges between concepts in this subgraph.</li>
                    ) : (
                      result.graph.relationships.map((r, i) => (
                        <li key={`${r.from}-${r.type}-${r.to}-${i}`} className="text-slate-800 dark:text-slate-200">
                          {r.from}{' '}
                          <span className="text-accent font-bold">—{r.type}→</span> {r.to}
                        </li>
                      ))
                    )}
                  </ul>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-emerald-200/70 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-900/40 p-6 shadow-sm">
              <h2 className="text-lg font-bold font-display text-slate-900 dark:text-white mb-4">
                4. Roadmap from graph (graphdb/roadmap_builder)
              </h2>
              {outcomes && outcomes.length > 0 ? (
                <LearningRoadmap
                  outcomes={outcomes}
                  startHereTo="/roadmap"
                />
              ) : (
                <p className="text-sm text-slate-500">No lessons were produced from this graph.</p>
              )}
              <p className="text-xs text-slate-500 mt-4">
                Lesson content generation is still a work in progress; “Start here” sends learners to the main roadmap
                experience for now.
              </p>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  )
}
