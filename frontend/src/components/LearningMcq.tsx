import { useId, useState, type ReactNode } from 'react'

export type LearningMcqOption = {
  id: string
  label: ReactNode
}

type LearningMcqProps = {
  title?: string
  icon?: string
  question: ReactNode
  options: LearningMcqOption[]
  correctOptionId: string
  /** Shown after the learner picks an answer */
  explanation?: ReactNode
  embedded?: boolean
}

export default function LearningMcq({
  title = 'Check your understanding',
  icon = 'quiz',
  question,
  options,
  correctOptionId,
  explanation,
  embedded = false,
}: LearningMcqProps) {
  const baseId = useId()
  const questionId = `${baseId}-question`
  const [chosen, setChosen] = useState<string | null>(null)
  const answered = chosen !== null

  const tryAgain = () => setChosen(null)

  const inner = (
      <div
        className="rounded-xl border border-amber-200/70 dark:border-amber-800/50 bg-white/85 dark:bg-slate-900/85 px-4 py-5 sm:px-6 sm:py-6 shadow-sm space-y-4"
        role="radiogroup"
        aria-labelledby={questionId}
      >
        <div id={questionId} className="text-slate-700 dark:text-slate-200 leading-relaxed">
          {question}
        </div>

        <ul className="space-y-2 list-none p-0 m-0">
          {options.map((opt) => {
            const picked = chosen === opt.id
            const isCorrectOpt = opt.id === correctOptionId
            let optionClass =
              'w-full text-left rounded-xl border-2 px-4 py-3 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900 '

            if (!answered) {
              optionClass +=
                'border-amber-200/80 dark:border-amber-800/40 bg-white dark:bg-slate-800/50 text-slate-800 dark:text-slate-100 hover:border-primary/50 hover:bg-storm-300/40 dark:hover:bg-slate-800 cursor-pointer'
            } else {
              if (isCorrectOpt) {
                optionClass +=
                  'border-emerald-500 dark:border-emerald-500/70 bg-emerald-50/90 dark:bg-emerald-950/30 text-slate-900 dark:text-slate-100 ring-2 ring-emerald-500/30'
              } else if (picked) {
                optionClass +=
                  'border-red-400 dark:border-red-500/70 bg-red-50/90 dark:bg-red-950/25 text-slate-900 dark:text-slate-100'
              } else {
                optionClass +=
                  'border-slate-200/80 dark:border-slate-600 bg-slate-50/80 dark:bg-slate-800/40 text-slate-500 dark:text-slate-400 opacity-80'
              }
            }

            return (
              <li key={opt.id}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={picked}
                  disabled={answered}
                  onClick={() => {
                    if (!answered) setChosen(opt.id)
                  }}
                  className={optionClass}
                >
                  {opt.label}
                </button>
              </li>
            )
          })}
        </ul>

        {answered && (
          <div
            className="space-y-2 pt-1 border-t border-amber-200/50 dark:border-amber-800/40"
            role="status"
          >
            <p
              className={`font-display font-extrabold text-lg ${
                chosen === correctOptionId
                  ? 'text-primary dark:text-primary-light'
                  : 'text-amber-800 dark:text-amber-200'
              }`}
            >
              {chosen === correctOptionId ? 'Correct!' : 'Not quite.'}
            </p>
            {explanation && (
              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{explanation}</p>
            )}
          </div>
        )}

        {answered && (
          <div className="pt-1">
            <button
              type="button"
              onClick={tryAgain}
              className="text-sm font-semibold text-primary hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        {!answered && (
          <p className="text-xs font-semibold text-primary dark:text-primary-light/90">Choose an answer</p>
        )}
      </div>
  )

  if (embedded) {
    return inner
  }

  return (
    <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-950/25 dark:to-amber-950/10 p-6 sm:p-8 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
      <h3 className="text-lg font-bold text-primary font-display mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary shrink-0" aria-hidden>
          {icon}
        </span>
        {title}
      </h3>
      {inner}
    </section>
  )
}
