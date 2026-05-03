import { useCallback, useEffect, useState, type DragEvent, type ReactNode } from 'react'

type LearningFillBlankProps = {
  /** Words available to move into the blank (shown as chips). */
  wordBank: string[]
  correctAnswer: string
  /** Content before the blank (inline). */
  before: ReactNode
  /** Content after the blank (inline). */
  after?: ReactNode
  /** Bump to reset chips + blank (e.g. try again). */
  resetKey: number
  onCorrect: () => void
  onIncorrect: () => void
}

export function gradeFillBlankAnswer(correctAnswer: string, reply: string): boolean {
  const t = reply.trim().toLowerCase().replace(/\s+/g, ' ')
  const target = correctAnswer.trim().toLowerCase()
  const esc = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`\\b${esc}\\b`, 'i').test(t)
}

export default function LearningFillBlank({
  wordBank: wordBankProp,
  correctAnswer,
  before,
  after,
  resetKey,
  onCorrect,
  onIncorrect,
}: LearningFillBlankProps) {
  const [bank, setBank] = useState<string[]>(() => [...wordBankProp])
  const [blank, setBlank] = useState<string | null>(null)

  useEffect(() => {
    setBank([...wordBankProp])
    setBlank(null)
  }, [resetKey, wordBankProp])

  const returnToBank = useCallback((w: string) => {
    setBank((b) => (b.includes(w) ? b : [...b, w]))
  }, [])

  const commitBlank = useCallback(
    (w: string) => {
      const normalized = w.trim().toLowerCase()
      if (blank === w) return

      const prev = blank
      if (prev && prev !== w) returnToBank(prev)

      setBank((b) => b.filter((x) => x !== w))
      setBlank(w)

      if (normalized === correctAnswer.trim().toLowerCase()) {
        onCorrect()
        return
      }

      onIncorrect()
      window.setTimeout(() => {
        setBlank(null)
        setBank([...wordBankProp])
      }, 1800)
    },
    [blank, correctAnswer, onCorrect, onIncorrect, returnToBank, wordBankProp]
  )

  const clearBlank = useCallback(() => {
    if (!blank) return
    returnToBank(blank)
    setBlank(null)
  }, [blank, returnToBank])

  const handleDragStart = (e: DragEvent, word: string) => {
    e.dataTransfer.setData('text/plain', word)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDropZoneDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDropZoneDrop = (e: DragEvent) => {
    e.preventDefault()
    const w = e.dataTransfer.getData('text/plain').trim()
    if (!w || !wordBankProp.includes(w)) return
    commitBlank(w)
  }

  return (
    <div className="space-y-4">
      <p className="text-slate-700 dark:text-slate-200 leading-relaxed text-base">
        {before}{' '}
        <span
          role="button"
          tabIndex={0}
          onDragOver={handleDropZoneDragOver}
          onDrop={handleDropZoneDrop}
          onClick={clearBlank}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              clearBlank()
            }
          }}
          className={`inline-flex min-w-[7rem] align-baseline justify-center px-2 py-0.5 mx-0.5 rounded-lg border-2 border-dashed transition-colors ${
            blank
              ? 'border-primary bg-storm-300/65 dark:bg-storm-700/35 text-slate-900 dark:text-white font-semibold cursor-pointer'
              : 'border-amber-400/70 dark:border-amber-600/50 bg-amber-50/40 dark:bg-amber-950/20 text-slate-500 dark:text-slate-400'
          }`}
          aria-label={blank ? `Filled with ${blank}. Click to clear.` : 'Drop zone for answer'}
        >
          {blank ?? '—'}
        </span>{' '}
        {after}
      </p>

      <div>
        <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Word bank</p>
        <div className="flex flex-wrap gap-2">
          {bank.map((w) => (
            <button
              key={w}
              type="button"
              draggable
              onDragStart={(e) => handleDragStart(e, w)}
              onClick={() => commitBlank(w)}
              className="rounded-xl border-2 border-amber-200/90 dark:border-amber-800/50 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-800 dark:text-slate-100 shadow-sm cursor-grab active:cursor-grabbing hover:border-primary/50 hover:bg-amber-50/50 dark:hover:bg-slate-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              {w}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
