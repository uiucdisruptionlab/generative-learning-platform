import { useState } from 'react';
import AppLayout from '../components/AppLayout';
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard';
import { usePersona } from '../contexts/PersonaContext';

const MOCK_PROFILE: LearnerProfile = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Alex Johnson',
  major_or_field: 'Business Administration',
  learning_goals: [
    'Master financial accounting principles and GAAP standards',
    'Develop strong analytical skills for financial statement analysis',
    'Prepare for CPA certification exam',
    'Learn data-driven decision making with Excel and Tableau',
  ],
  interests: [
    'Financial Markets',
    'Investment Analysis',
    'Corporate Finance',
    'Data Analytics',
    'Economics',
    'Entrepreneurship',
  ],
  academic_level: 'Junior',
  weekly_hours: 15,
  preferred_formats: [
    'Interactive practice problems',
    'Video lectures',
    'Reading materials',
    'Case studies',
  ],
  llm_profile: {
    learning_style: 'Visual and Kinesthetic',
    pace_preference: 'Moderate with deep understanding',
    strength_areas: 'Quantitative analysis, Pattern recognition',
    growth_areas: 'Theoretical frameworks, Long-form writing',
    engagement_level: 'Highly motivated',
  },
  created_at: '2024-01-15T08:30:00Z',
  updated_at: '2024-03-20T14:22:00Z',
};

function getPersonaProfile(personaData: typeof import('../data/personas').PERSONAS[keyof typeof import('../data/personas').PERSONAS] | null): LearnerProfile {
  if (!personaData) {
    return MOCK_PROFILE;
  }

  const learningGoalsMap: Record<string, string[]> = {
    alice: [
      'Build strong programming fundamentals in Python',
      'Develop problem-solving skills through hands-on coding',
      'Master data structures and algorithms',
      'Prepare for data science applications',
    ],
    bob: [
      'Understand capital markets and financing mechanisms',
      'Analyze economic development case studies',
      'Master financial analysis for development projects',
      'Apply theory to real-world policy scenarios',
    ],
    charles: [
      'Master financial accounting principles and GAAP standards',
      'Excel at managerial accounting decision-making',
      'Prepare for CPA certification exam',
      'Achieve high proficiency through intensive study',
    ],
  };

  const interestsMap: Record<string, string[]> = {
    alice: ['Python Programming', 'Data Science', 'Algorithms', 'Machine Learning', 'Finance', 'Technology'],
    bob: ['Economic Policy', 'Financial Markets', 'Urban Development', 'Real Estate', 'Sustainable Finance', 'Case Studies'],
    charles: ['Accounting Standards', 'Financial Reporting', 'Cost Analysis', 'Auditing', 'Tax Planning', 'Business Strategy'],
  };

  const preferredFormatsMap: Record<string, string[]> = {
    alice: ['Video lectures', 'Hands-on coding problems', 'Interactive tutorials', 'Code examples'],
    bob: ['In-depth reading materials', 'AI discussion sessions', 'Case study analysis', 'Research papers'],
    charles: ['Flashcard reviews', 'Practice quizzes', 'Problem sets', 'Mock exams'],
  };

  return {
    id: personaData.id,
    name: personaData.name,
    major_or_field: personaData.major,
    learning_goals: learningGoalsMap[personaData.id] || [],
    interests: interestsMap[personaData.id] || [],
    academic_level: personaData.experienceLevel === 'beginner' ? 'Sophomore' : personaData.experienceLevel === 'intermediate' ? 'Junior' : 'Senior',
    weekly_hours: personaData.hoursPerWeek,
    preferred_formats: preferredFormatsMap[personaData.id] || [],
    llm_profile: {
      learning_style: personaData.learningStyle,
      pace_preference: personaData.hoursPerWeek >= 10 ? 'Fast-paced and intensive' : personaData.hoursPerWeek >= 5 ? 'Moderate with deep understanding' : 'Steady and consistent',
      strength_areas: personaData.experienceLevel === 'advanced' ? 'Subject matter expertise, Critical analysis' : personaData.experienceLevel === 'intermediate' ? 'Foundational knowledge, Dedicated practice' : 'Enthusiasm to learn, Strong work ethic',
      growth_areas: personaData.experienceLevel === 'beginner' ? 'Building foundational skills, Confidence in application' : 'Advanced concepts, Real-world application',
      engagement_level: 'Highly motivated',
    },
    created_at: '2024-01-15T08:30:00Z',
    updated_at: '2024-03-20T14:22:00Z',
  };
}

export default function ProfilePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { persona } = usePersona();
  const profile = getPersonaProfile(persona);

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      settingsOpen={settingsOpen}
      onToggleSettings={() => setSettingsOpen(!settingsOpen)}
      title="My Profile"
      description="View and manage your learning profile and preferences"
    >
      <div className="max-w-[1200px] w-full min-w-0 mx-auto px-8 lg:px-12 py-8 lg:py-12">
        <LearnerProfileCard profile={profile} />
      </div>
    </AppLayout>
  );
}
