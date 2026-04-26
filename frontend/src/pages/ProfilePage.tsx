import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout';
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard';
import { usePersona } from '../contexts/PersonaContext';
import { fetchStudent, type StudentProfile } from '../api/home';

function mapStudentProfile(student: StudentProfile): LearnerProfile {
  const goals = student.learning_goals
    ? Object.entries(student.learning_goals).map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    : []
  const llmProfile = student.llm_profile
    ? Object.fromEntries(
        Object.entries(student.llm_profile).map(([key, value]) => [
          key === 'learning_style_summary' ? 'Learning Style' : key,
          value,
        ]),
      )
    : null
  return {
    id: student.id,
    name: student.name,
    major_or_field: student.major_or_field || '',
    learning_goals: goals,
    interests: student.interests || [],
    academic_level: student.academic_level || '',
    weekly_hours: student.weekly_hours || 0,
    preferred_formats: student.preferred_formats || [],
    llm_profile: llmProfile,
    created_at: student.created_at || '',
    updated_at: student.updated_at || '',
  };
}

export default function ProfilePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { studentId } = usePersona();
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchStudent(studentId)
      .then((student) => {
        if (!cancelled) setProfile(mapStudentProfile(student));
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [studentId]);

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
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-24 text-gray-400 dark:text-gray-500">
            <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            <p className="text-sm">Loading your profile…</p>
          </div>
        ) : error ? (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            Unable to load profile right now.
          </div>
        ) : profile ? (
          <LearnerProfileCard profile={profile} />
        ) : (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            No profile data found.
          </div>
        )}
      </div>
    </AppLayout>
  );
}
