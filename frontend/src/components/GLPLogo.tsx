import glpLogo from '../assets/glp-logo.png'

type GLPLogoProps = {
  compact?: boolean
  className?: string
}

export default function GLPLogo({ compact = false, className = '' }: GLPLogoProps) {
  return (
    <div className={`group flex items-center gap-2 ${className}`}>
      <div className={`flex ${compact ? 'h-6 w-6' : 'h-8 w-8'} items-center justify-center rounded-[1rem] bg-white shadow-xl shadow-illini-orange/20 ring-1 ring-white/50 overflow-hidden`}>
        <img src={glpLogo} alt="GLP Logo" className="h-4 w-4 object-contain object-center" />
      </div>
      {!compact && (
        <div className="min-w-0">
          <p className="text-sm font-bold uppercase tracking-[0.25em] text-illini-blue">GLP</p>
          <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">Generative learning experience</p>
        </div>
      )}
    </div>
  )
}
