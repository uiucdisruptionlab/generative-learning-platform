import { Routes, Route, Navigate } from 'react-router-dom'
import { PersonaProvider } from './contexts/PersonaContext'
import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import RoadmapPage from './pages/RoadmapPage'
import IncomeStatementPage from './pages/IncomeStatementPage'
import CoursesPage from './pages/CoursesPage'
import CS101VariablesPage from './pages/CS101VariablesPage'
import MKTG440SEOPage from './pages/MKTG440SEOPage'
import HIST102IndustrialPage from './pages/HIST102IndustrialPage'
import ECON201GDPPage from './pages/ECON201GDPPage'
import LessonPage from './pages/LessonPage'
import InteractiveLessonPage from './pages/InteractiveLessonPage'

function App() {
  return (
    <PersonaProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="/module/income-statement" element={<IncomeStatementPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/roadmap/cs101" element={<RoadmapPage />} />
        <Route path="/module/cs101-variables" element={<CS101VariablesPage />} />
        <Route path="/roadmap/mktg440" element={<RoadmapPage />} />
        <Route path="/module/mktg440-seo" element={<MKTG440SEOPage />} />
        <Route path="/roadmap/hist102" element={<RoadmapPage />} />
        <Route path="/module/hist102-industrial" element={<HIST102IndustrialPage />} />
        <Route path="/roadmap/econ201" element={<RoadmapPage />} />
        <Route path="/module/econ201-gdp" element={<ECON201GDPPage />} />
        <Route path="/roadmap/python" element={<RoadmapPage />} />
        <Route path="/roadmap/financing" element={<RoadmapPage />} />
        <Route path="/roadmap/accounting" element={<RoadmapPage />} />
        <Route path="/lesson" element={<InteractiveLessonPage />} />
        <Route path="/lesson/:lessonId/interactive" element={<InteractiveLessonPage />} />
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
      </Routes>
    </PersonaProvider>
  )
}

export default App
