import { Routes, Route, Navigate } from 'react-router-dom'
import { PersonaProvider } from './contexts/PersonaContext'
import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import RoadmapPage from './pages/RoadmapPage'
import CoursesPage from './pages/CoursesPage'
import InteractiveLessonPage from './pages/InteractiveLessonPage'
import LessonTranscriptPage from './pages/LessonTranscriptPage'

function App() {
  return (
    <PersonaProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="/roadmap/:courseId" element={<RoadmapPage />} />
        <Route path="/lesson" element={<InteractiveLessonPage />} />
        <Route path="/lesson/:lessonId/interactive" element={<InteractiveLessonPage />} />
        <Route path="/lesson/transcript" element={<LessonTranscriptPage />} />
      </Routes>
    </PersonaProvider>
  )
}

export default App
