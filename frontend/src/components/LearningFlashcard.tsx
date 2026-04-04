import { useState, type ReactNode } from 'react'

type LearningFlashcardProps = {
  /** Section heading when `embedded` is false */
  title?: string
  icon?: string
  front: ReactNode
  back: ReactNode
  hintFront?: string
  hintBack?: string
  /** Omit outer section + title — use inside a parent practice card */
  embedded?: boolean
}

export default function LearningFlashcard({
  title = 'Quick flashcard',
  icon = 'flip_to_back',
  front,
  back,
  hintFront = 'Click the card to reveal the answer',
  hintBack = 'Click again to see the question',
  embedded = false,
}: LearningFlashcardProps) {
  const [flipped, setFlipped] = useState(false)

  const flipBody = (
      <button
        type="button"
        onClick={() => setFlipped((f) => !f)}
        aria-pressed={flipped}
        className={`w-full text-left rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 [perspective:1200px] ${
          embedded
            ? 'focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900/85'
            : 'focus-visible:ring-offset-amber-50 dark:focus-visible:ring-offset-slate-900'
        }`}
      >
        <div
          className={`relative min-h-[13rem] sm:min-h-[11rem] w-full transition-transform duration-500 ease-out [transform-style:preserve-3d] motion-reduce:transition-none ${
            flipped ? '[transform:rotateY(180deg)]' : ''
          }`}
        >
          <div className="absolute inset-0 flex flex-col justify-center rounded-xl border border-amber-200/70 dark:border-amber-800/50 bg-white/85 dark:bg-slate-900/85 px-4 py-5 sm:px-6 sm:py-6 [backface-visibility:hidden] shadow-sm">
            <div className="text-slate-700 dark:text-slate-200 leading-relaxed">{front}</div>
            <p className="mt-4 text-xs font-semibold text-primary dark:text-primary-light/90">{hintFront}</p>
          </div>
          <div className="absolute inset-0 flex flex-col justify-center rounded-xl border border-amber-200/70 dark:border-amber-800/50 bg-white/85 dark:bg-slate-900/85 px-4 py-5 sm:px-6 sm:py-6 [backface-visibility:hidden] [transform:rotateY(180deg)] shadow-sm">
            <div className="text-slate-700 dark:text-slate-200 leading-relaxed">{back}</div>
            <p className="mt-4 text-xs font-semibold text-primary dark:text-primary-light/90">{hintBack}</p>
          </div>
        </div>
      </button>
  )

  if (embedded) {
    return flipBody
  }

  return (
    <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-950/25 dark:to-amber-950/10 p-6 sm:p-8 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
      <h3 className="text-lg font-bold text-primary font-display mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary shrink-0" aria-hidden>
          {icon}
        </span>
        {title}
      </h3>
      {flipBody}
    </section>
  )
}
