import LearningFillBlank, { gradeFillBlankAnswer } from './LearningFillBlank'
import LearningFlashcard from './LearningFlashcard'
import LearningMcq from './LearningMcq'

export type IncomePracticeType = 'open' | 'flashcard' | 'mcq' | 'fill'

export type OpenPracticeFeedback = 'idle' | 'correct' | 'incorrect'

const PRACTICE_TYPE_OPTIONS: { value: IncomePracticeType; label: string }[] = [
  { value: 'open', label: 'Open-ended (chat)' },
  { value: 'fill', label: 'Fill in the blank' },
  { value: 'flashcard', label: 'Flashcard' },
  { value: 'mcq', label: 'Multiple choice' },
]

const INCOME_FILL_BANK = ['expenses', 'assets', 'liabilities', 'dividends']

type IncomeStatementPracticeCellProps = {
  practiceType: IncomePracticeType
  onPracticeTypeChange: (t: IncomePracticeType) => void
  openFeedback: OpenPracticeFeedback
  onResetOpenPractice: () => void
  fillFeedback: OpenPracticeFeedback
  fillResetKey: number
  onFillResult: (result: 'correct' | 'incorrect') => void
  onResetFillPractice: () => void
}

/** Chat grading for the income-statement fill-in (missing word: expenses). */
export function gradeIncomeStatementFillBlank(answer: string): boolean {
  return gradeFillBlankAnswer('expenses', answer)
}

/** Mock grader for the coffee shop scenario (net income = $30,000). */
export function gradeCoffeeShopNetIncome(answer: string): boolean {
  const raw = answer.trim().toLowerCase()
  const noComma = raw.replace(/,/g, '')
  const compact = noComma.replace(/\$/g, '').replace(/\s+/g, ' ')

  if (/\b30000\b/.test(compact)) return true
  if (/\b30\s*000\b/.test(compact)) return true
  if (/\b30k\b/.test(raw.replace(/\s/g, ''))) return true
  if (noComma.includes('30000')) return true
  if (/thirty\s*thousand/.test(raw)) return true
  if (/(\$|^|\s)30(\.0+)?\s*k\b/.test(raw)) return true

  return false
}

export default function IncomeStatementPracticeCell({
  practiceType,
  onPracticeTypeChange,
  openFeedback,
  onResetOpenPractice,
  fillFeedback,
  fillResetKey,
  onFillResult,
  onResetFillPractice,
}: IncomeStatementPracticeCellProps) {
  return (
    <section className="rounded-2xl bg-gradient-to-br from-amber-50 to-emerald-50 dark:from-amber-950/30 dark:to-emerald-950/20 p-6 border-2 border-amber-200/80 dark:border-amber-800/40 shadow-soft">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-4 min-w-0">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white font-display flex items-center gap-2 shrink-0">
          <span className="material-symbols-outlined text-primary" aria-hidden>
            edit
          </span>
          Try it yourself
        </h3>
        <div className="flex flex-col gap-1 w-full sm:w-auto sm:min-w-[13.5rem] shrink-0">
          <label htmlFor="income-practice-type" className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            Question type
          </label>
          <select
            id="income-practice-type"
            value={practiceType}
            onChange={(e) => onPracticeTypeChange(e.target.value as IncomePracticeType)}
            className="rounded-xl border-2 border-amber-200/90 dark:border-amber-800/50 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-800 dark:text-slate-100 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            {PRACTICE_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {practiceType === 'open' && (
        <div className="space-y-4">
          <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
            Imagine a coffee shop makes <strong className="text-slate-900 dark:text-white">$200,000</strong> in revenue
            this year. Their costs include:
          </p>
          <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 space-y-1">
            <li>Coffee beans and supplies: $60,000</li>
            <li>Staff wages: $80,000</li>
            <li>Rent and utilities: $30,000</li>
          </ul>
          <p className="text-slate-600 dark:text-slate-300">
            What&apos;s their net income? Type your answer in the chat below.
          </p>

          {openFeedback === 'correct' && (
            <div
              className="rounded-xl border-2 border-primary/40 bg-emerald-50/90 dark:bg-emerald-950/30 px-4 py-3 text-sm text-slate-800 dark:text-slate-100"
              role="status"
            >
              <p className="font-bold text-primary dark:text-primary-light mb-1">Nice work — that&apos;s right!</p>
              <p className="text-slate-700 dark:text-slate-300">
                Net income is <strong className="text-slate-900 dark:text-white">$30,000</strong> ($200,000 revenue minus
                $170,000 in total expenses).
              </p>
              <button
                type="button"
                onClick={onResetOpenPractice}
                className="mt-3 text-sm font-semibold text-primary hover:underline"
              >
                Try another
              </button>
            </div>
          )}

          {openFeedback === 'incorrect' && (
            <div
              className="rounded-xl border-2 border-amber-600/40 dark:border-amber-500/40 bg-amber-50/80 dark:bg-amber-950/25 px-4 py-3 text-sm text-slate-800 dark:text-slate-100"
              role="status"
            >
              <p className="font-bold text-amber-900 dark:text-amber-200 mb-1">Not quite — give it another shot</p>
              <p className="text-slate-700 dark:text-slate-300">
                Add up the expenses, subtract from revenue, or type the net income number. You can ask again in the chat whenever you&apos;re ready.
              </p>
              <button
                type="button"
                onClick={onResetOpenPractice}
                className="mt-3 text-sm font-semibold text-primary hover:underline"
              >
                Reset and try again
              </button>
            </div>
          )}
        </div>
      )}

      {practiceType === 'fill' && (
        <div className="space-y-4">
          {(fillFeedback === 'idle' || fillFeedback === 'incorrect') && (
            <>
              <LearningFillBlank
                wordBank={INCOME_FILL_BANK}
                correctAnswer="expenses"
                resetKey={fillResetKey}
                onCorrect={() => onFillResult('correct')}
                onIncorrect={() => onFillResult('incorrect')}
                before={
                  <>
                    On a basic income statement, <strong className="text-slate-900 dark:text-white">net income</strong>{' '}
                    equals revenue minus total
                  </>
                }
                after={<>.</>}
              />
              <p className="text-slate-600 dark:text-slate-300 text-sm">
                Drag the correct answer or type in chat.
              </p>
            </>
          )}

          {fillFeedback === 'correct' && (
            <div
              className="rounded-xl border-2 border-primary/40 bg-emerald-50/90 dark:bg-emerald-950/30 px-4 py-3 text-sm text-slate-800 dark:text-slate-100"
              role="status"
            >
              <p className="font-bold text-primary dark:text-primary-light mb-1">Correct!</p>
              <p className="text-slate-700 dark:text-slate-300">
                Net income is revenue minus total <strong className="text-slate-900 dark:text-white">expenses</strong>{' '}
                for the period.
              </p>
              <button
                type="button"
                onClick={onResetFillPractice}
                className="mt-3 text-sm font-semibold text-primary hover:underline"
              >
                Try again
              </button>
            </div>
          )}

          {fillFeedback === 'incorrect' && (
            <div
              className="rounded-xl border-2 border-amber-600/40 dark:border-amber-500/40 bg-amber-50/80 dark:bg-amber-950/25 px-4 py-3 text-sm text-slate-800 dark:text-slate-100"
              role="status"
            >
              <p className="font-bold text-amber-900 dark:text-amber-200 mb-1">Not quite</p>
              <p className="text-slate-700 dark:text-slate-300">
                Try another word from the bank, or type <strong className="text-slate-900 dark:text-white">expenses</strong> in
                the chat.
              </p>
              <button
                type="button"
                onClick={onResetFillPractice}
                className="mt-3 text-sm font-semibold text-primary hover:underline"
              >
                Reset and try again
              </button>
            </div>
          )}
        </div>
      )}

      {practiceType === 'flashcard' && (
        <div className="space-y-2">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Flip the card to check your recall — no chat needed for this mode.
          </p>
          <LearningFlashcard
            embedded
            front={
              <>
                <p className="text-slate-800 dark:text-slate-100 font-display font-bold text-base mb-1">Question</p>
                <p>
                  On a simple income statement, how do you get from{' '}
                  <strong className="text-slate-900 dark:text-white">total revenue</strong> to{' '}
                  <strong className="text-slate-900 dark:text-white">net income</strong>?
                </p>
              </>
            }
            back={
              <>
                <p className="text-slate-800 dark:text-slate-100 font-display font-bold text-base mb-1">Answer</p>
                <p>
                  Subtract <strong className="text-slate-900 dark:text-white">total expenses</strong> from revenue for the
                  same period. What is left is net income: profit if positive, a loss if negative.
                </p>
              </>
            }
          />
        </div>
      )}

      {practiceType === 'mcq' && (
        <div className="space-y-2">
          <p className="text-sm text-slate-600 dark:text-slate-400">Tap an option — feedback appears instantly below.</p>
          <LearningMcq
            embedded
            key="income-mcq"
            question={
              <p>
                On a standard income statement shown to investors, which line best describes{' '}
                <strong className="text-slate-900 dark:text-white">profit after all expenses</strong> for the reporting
                period?
              </p>
            }
            options={[
              { id: 'rev', label: 'Gross revenue' },
              { id: 'cogs', label: 'Cost of goods sold only' },
              { id: 'ni', label: 'Net income' },
              { id: 'cash', label: 'Cash on hand at year-end' },
            ]}
            correctOptionId="ni"
            explanation={
              <>
                <strong className="text-slate-800 dark:text-slate-200">Net income</strong> is often called the bottom line:
                revenue minus all expenses for that period. It is not the same as cash in the bank (that&apos;s on the
                balance sheet and cash flow statement).
              </>
            }
          />
        </div>
      )}
    </section>
  )
}
