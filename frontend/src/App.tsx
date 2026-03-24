import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import RoadmapPage from './pages/RoadmapPage'
import IncomeStatementPage from './pages/IncomeStatementPage'
import CoursesPage from './pages/CoursesPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/roadmap" element={<RoadmapPage />} />
      <Route path="/module/income-statement" element={<IncomeStatementPage />} />
      <Route path="/courses" element={<CoursesPage />} />
    </Routes>
  )
}

export default App
