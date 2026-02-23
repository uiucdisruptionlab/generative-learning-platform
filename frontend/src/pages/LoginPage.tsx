import { Link } from 'react-router-dom'

export default function LoginPage() {
  return (
    <div
      className="min-h-screen flex flex-col relative"
      style={{ background: 'linear-gradient(135deg, #fef9c3 0%, #fef3c7 20%, #fff7ed 40%, #fed7aa 60%, #fecaca 80%, #fef3c7 100%)' }}
    >
      <div className="learning-pathway absolute w-full h-full overflow-hidden z-0 pointer-events-none">
        <svg className="absolute w-full h-full opacity-30" fill="none" viewBox="0 0 1440 800" xmlns="http://www.w3.org/2000/svg">
          <path className="stroke-dasharray-[10,10]" d="M-50 750C200 650 400 700 600 500C800 300 1100 400 1490 100" stroke="#2c5926" strokeWidth={4} />
          <path className="stroke-dasharray-[10,10]" d="M1500 750C1200 600 1000 650 720 400C440 150 200 200 -50 50" stroke="#f59e0b" strokeWidth={4} />
          <path className="stroke-dasharray-[10,10]" d="M100 200C400 350 800 150 1200 300" stroke="#f87171" strokeWidth={3} />
          <circle className="opacity-25" cx="10%" cy="20%" fill="#fde68a" r="40" />
          <circle className="opacity-25" cx="85%" cy="75%" fill="#fed7aa" r="60" />
          <circle className="opacity-25" cx="90%" cy="15%" fill="#fecaca" r="30" />
          <circle className="opacity-20" cx="50%" cy="85%" fill="#fbbf24" r="50" />
          <circle className="opacity-20" cx="70%" cy="40%" fill="#fdba74" r="35" />
          <path className="opacity-40" d="M200 800 L300 600" stroke="white" strokeWidth={2} />
          <path className="opacity-40" d="M220 800 L320 600" stroke="white" strokeWidth={2} />
        </svg>
        <div className="absolute bottom-[15%] left-[10%] rotate-45 text-primary/15">
          <span className="material-symbols-outlined text-[120px]">rocket_launch</span>
        </div>
        <div className="absolute top-[10%] right-[12%] -rotate-[15deg] text-amber-500/20">
          <span className="material-symbols-outlined text-[80px]">rocket_launch</span>
        </div>
        <div className="absolute top-[60%] left-[5%] rotate-12 text-rose-400/15">
          <span className="material-symbols-outlined text-[60px]">rocket_launch</span>
        </div>
      </div>

      <header className="relative z-10 flex items-center justify-between whitespace-nowrap px-8 py-5 bg-white/95 backdrop-blur-md border-b border-slate-200/80">
        <Link to="/login" className="flex items-center gap-4">
          <div className="size-12 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary ring-1 ring-primary/20 shrink-0">
            <span className="material-symbols-outlined text-3xl font-light">rocket_launch</span>
          </div>
          <h2 className="text-slate-900 text-base font-bold leading-tight font-logo tracking-normal">Generative Learning Platform</h2>
        </Link>
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-700 hover:text-primary transition-colors">
            <span className="material-symbols-outlined text-[22px]">help</span>
            Support
          </button>
        </div>
      </header>

      <main className="relative z-10 flex-grow flex items-center justify-center p-6">
        <div className="max-w-[480px] w-full bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.1)] border-2 border-slate-200 overflow-hidden">
            <div className="h-48 bg-emerald-100 flex flex-col items-center justify-center overflow-hidden border-b border-emerald-200/50">
              <span className="material-symbols-outlined text-primary text-6xl drop-shadow-md">rocket_launch</span>
            </div>
          <div className="p-8 md:p-12 flex flex-col items-center text-center">
            <h1 className="text-4xl font-extrabold text-slate-800 mb-3 tracking-tight font-display">Sign in to GLP</h1>
            <p className="text-slate-600 text-base leading-relaxed mb-10 max-w-[340px]">
              Access your generative learning resources through your institutional account.
            </p>
            <Link
              to="/home"
              className="w-full bg-gradient-to-r from-primary to-primary-light hover:shadow-xl hover:shadow-primary/30 text-white font-bold py-5 px-8 rounded-2xl transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-4 shadow-lg shadow-primary/25 mb-8"
            >
              <div className="bg-white rounded-lg p-1.5 flex items-center justify-center shadow-inner">
                <span className="material-symbols-outlined text-primary font-bold text-2xl">school</span>
              </div>
              <span className="text-lg">Login with Canvas</span>
            </Link>
            <div className="bg-emerald-50/80 p-5 rounded-2xl border-2 border-primary/20 w-full mb-10">
              <div className="flex items-start gap-4 text-left">
                <span className="material-symbols-outlined text-primary text-[24px]">info</span>
                <p className="text-sm text-slate-700 leading-normal">
                  You will be redirected to the <span className="font-bold text-slate-900 underline decoration-primary/30">UIUC Canvas authentication service</span> to securely verify your identity.
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-6 w-full">
              <div className="h-[2px] bg-slate-100 w-full rounded-full" />
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-slate-500 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-primary">verified_user</span>
                  Secure Login
                </span>
                <a href="#" className="text-primary font-bold hover:underline transition-colors">Trouble signing in?</a>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="relative z-10 py-10 px-6 text-center">
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4 mb-6">
          <a href="#" className="text-slate-600 font-semibold text-sm hover:text-primary transition-colors">Privacy Policy</a>
          <a href="#" className="text-slate-600 font-semibold text-sm hover:text-primary transition-colors">Terms of Service</a>
          <a href="#" className="text-slate-600 font-semibold text-sm hover:text-primary transition-colors">UIUC Support</a>
          <a href="#" className="text-slate-600 font-semibold text-sm hover:text-primary transition-colors">Contact GLP</a>
        </div>
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="material-symbols-outlined text-primary/40 text-sm">rocket</span>
          <p className="text-slate-500 text-[11px] uppercase tracking-[0.15em] font-bold">
            © 2024 Generative Learning Platform (GLP). All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
