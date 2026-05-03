import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout';
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard';
import { usePersona } from '../contexts/PersonaContext';
import { fetchStudent, type StudentProfile } from '../api/home';

function titleCaseSnake(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function learningGoalsToDisplayList(
  goals: NonNullable<StudentProfile['learning_goals']>,
): string[] {
  const g = goals as Record<string, unknown>;
  const out: string[] = [];

  const asStr = (v: unknown): string | null => {
    if (v === null || v === undefined) return null;
    if (typeof v === 'object') return null;
    const s = String(v).trim();
    return s || null;
  };

  const fmtEnumish = (s: string) =>
    /^[a-z0-9_]+$/i.test(s) && s.includes('_') ? titleCaseSnake(s) : s;

  const primary = asStr(g.primary_focus);
  if (primary) out.push(primary);

  const coding = asStr(g.coding_experience);
  if (coding) out.push(`Coding experience: ${fmtEnumish(coding)}`);

  const familiarity = asStr(g.topic_familiarity);
  if (familiarity) out.push(`Topic familiarity: ${fmtEnumish(familiarity)}`);

  const handled = new Set(['primary_focus', 'coding_experience', 'topic_familiarity']);
  for (const [key, value] of Object.entries(g)) {
    if (handled.has(key)) continue;
    const s = asStr(value);
    if (!s) continue;
    const label =
      key === 'target_course' || key === 'course' ? 'Course focus' : titleCaseSnake(key);
    out.push(`${label}: ${fmtEnumish(s)}`);
  }

  return out;
}

function formatRoadmapProgress(progress: unknown): string {
  if (!progress || typeof progress !== 'object' || Array.isArray(progress)) return '';
  const lines: string[] = [];
  for (const [courseId, raw] of Object.entries(progress as Record<string, unknown>)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue;
    const cp = raw as Record<string, unknown>;
    const completed = Array.isArray(cp.completed_lessons)
      ? (cp.completed_lessons as string[])
      : [];
    const current = cp.current_lesson_id != null ? String(cp.current_lesson_id) : '—';
    const courseLabel = titleCaseSnake(courseId.replace(/-/g, '_'));
    const n = completed.length;
    const summary =
      n === 0
        ? `Starting out · next up: ${current}`
        : `${n} lesson${n === 1 ? '' : 's'} done (${completed.join(', ')}) · current: ${current}`;
    lines.push(`${courseLabel}: ${summary}`);
  }
  return lines.join('\n\n');
}

function formatEnumishString(s: string): string {
  const t = s.trim();
  if (!t) return '';
  if (/^[a-z0-9_]+$/i.test(t) && t.includes('_')) return titleCaseSnake(t);
  return t;
}

/** Normalize API llm_profile into display keys + string values (no raw JSON in the card). */
function mapLlmProfileForDisplay(
  raw: NonNullable<StudentProfile['llm_profile']>,
): Record<string, string> | null {
  const out: Record<string, string> = {};

  const style = raw.learning_style_summary != null ? String(raw.learning_style_summary).trim() : '';
  if (style) out['Learning Style'] = style;

  const notes = raw.notes != null ? String(raw.notes).trim() : '';
  if (notes) out['Notes'] = notes;

  const conf = raw.subject_confidence != null ? String(raw.subject_confidence).trim() : '';
  if (conf) out['Prior Experience'] = formatEnumishString(conf);

  if (
    raw.roadmap_progress != null &&
    typeof raw.roadmap_progress === 'object' &&
    !Array.isArray(raw.roadmap_progress)
  ) {
    const formatted = formatRoadmapProgress(raw.roadmap_progress);
    if (formatted.trim()) out['Roadmap progress'] = formatted;
  }

  const handled = new Set([
    'learning_style_summary',
    'notes',
    'subject_confidence',
    'roadmap_progress',
  ]);
  for (const [key, value] of Object.entries(raw)) {
    if (handled.has(key)) continue;
    if (value === null || value === undefined) continue;
    const label = titleCaseSnake(key);
    if (typeof value === 'object') {
      const s = JSON.stringify(value);
      if (s !== '{}' && s !== '[]') out[label] = s;
    } else {
      const sv = String(value).trim();
      if (sv) out[label] = formatEnumishString(sv);
    }
  }

  return Object.keys(out).length > 0 ? out : null;
}

function mapStudentProfile(student: StudentProfile): LearnerProfile {
  const goals = student.learning_goals ? learningGoalsToDisplayList(student.learning_goals) : [];
  const llmProfile = student.llm_profile ? mapLlmProfileForDisplay(student.llm_profile) : null;
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
