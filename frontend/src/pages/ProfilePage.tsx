import { useState } from 'react';
import AppLayout from '../components/AppLayout';
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard';

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

function loadProfile(): LearnerProfile {
  try {
    const stored = localStorage.getItem('glp_learner_profile');
    if (stored) return JSON.parse(stored) as LearnerProfile;
  } catch {
    // ignore parse errors
  }
  return MOCK_PROFILE;
}

export default function ProfilePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profile] = useState<LearnerProfile>(loadProfile);

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
