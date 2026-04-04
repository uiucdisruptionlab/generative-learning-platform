import { Routes, Route, Navigate } from 'react-router-dom'
import { PersonaProvider } from './contexts/PersonaContext'
import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import RoadmapPage from './pages/RoadmapPage'
import IncomeStatementPage from './pages/IncomeStatementPage'
import CoursesPage from './pages/CoursesPage'
import CS101RoadmapPage from './pages/CS101RoadmapPage'
import CS101VariablesPage from './pages/CS101VariablesPage'
import MKTG440RoadmapPage from './pages/MKTG440RoadmapPage'
import MKTG440SEOPage from './pages/MKTG440SEOPage'
import HIST102RoadmapPage from './pages/HIST102RoadmapPage'
import HIST102IndustrialPage from './pages/HIST102IndustrialPage'
import ECON201RoadmapPage from './pages/ECON201RoadmapPage'
import ECON201GDPPage from './pages/ECON201GDPPage'
import PythonRoadmapPage from './pages/PythonRoadmapPage'
import FinancingRoadmapPage from './pages/FinancingRoadmapPage'
import AccountingRoadmapPage from './pages/AccountingRoadmapPage'

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
        <Route path="/roadmap/cs101" element={<CS101RoadmapPage />} />
        <Route path="/module/cs101-variables" element={<CS101VariablesPage />} />
        <Route path="/roadmap/mktg440" element={<MKTG440RoadmapPage />} />
        <Route path="/module/mktg440-seo" element={<MKTG440SEOPage />} />
        <Route path="/roadmap/hist102" element={<HIST102RoadmapPage />} />
        <Route path="/module/hist102-industrial" element={<HIST102IndustrialPage />} />
        <Route path="/roadmap/econ201" element={<ECON201RoadmapPage />} />
        <Route path="/module/econ201-gdp" element={<ECON201GDPPage />} />
        <Route path="/roadmap/python" element={<PythonRoadmapPage />} />
        <Route path="/roadmap/financing" element={<FinancingRoadmapPage />} />
        <Route path="/roadmap/accounting" element={<AccountingRoadmapPage />} />
      </Routes>
    </PersonaProvider>
  )
}

export default App
