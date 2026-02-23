import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import CareerPage from './pages/CareerPage'
import CoursesPage from './pages/CoursesPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      {/* /home → HomePage (Personalized Learning: Welcome back, skill radar, recommendations) */}
      {/* /dashboard → Career Hub (Professional Profile, AI Resume Tailoring) */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/dashboard" element={<CareerPage />} />
      <Route path="/courses" element={<CoursesPage />} />
    </Routes>
  )
}

export default App
