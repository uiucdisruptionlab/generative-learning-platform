import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout';
import LearnerProfileCard, { type LearnerProfile } from '../components/LearnerProfileCard';
import { usePersona } from '../contexts/PersonaContext';
import { fetchStudent, updateStudent, type StudentProfile, type StudentProfileUpdate } from '../api/home';

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

function listToText(values?: string[]): string {
  return (values ?? []).join(', ');
}

function textToList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function suggestedLearningStyle(formatsText: string, confidence: string): string {
  const formats = textToList(formatsText);
  if (!formats.length) {
    return 'Prefers guided explanations and targeted practice questions.';
  }
  const formatPhrase = formats.length === 1
    ? formats[0]
    : `${formats.slice(0, -1).join(', ')} and ${formats[formats.length - 1]}`;
  const confidenceText = confidence.trim();
  return `Prefers learning through ${formatPhrase}${confidenceText ? `; current confidence is ${confidenceText}` : ''}.`;
}

const ACADEMIC_LEVEL_OPTIONS = [
  'Freshman',
  'Sophomore',
  'Junior',
  'Senior',
  'Undergraduate',
  'Graduate',
];

const SUBJECT_CONFIDENCE_OPTIONS = [
  'totally_new',
  'beginner',
  'somewhat_familiar',
  'comfortable',
  'advanced',
];

const PREFERRED_FORMAT_OPTIONS = [
  'videos',
  'reading',
  'flashcards',
  'MCQs',
  'worked examples',
  'practice questions',
  'AI interaction',
];

type ProfileFormState = {
  name: string;
  major_or_field: string;
  academic_level: string;
  weekly_hours: string;
  primary_focus: string;
  target_course: string;
  career_goal: string;
  interests: string;
  preferred_formats: string;
  learning_style_summary: string;
  subject_confidence: string;
  notes: string;
}

function initialFormState(student: StudentProfile): ProfileFormState {
  const goals = student.learning_goals ?? {};
  const llm = student.llm_profile ?? {};
  return {
    name: student.name ?? '',
    major_or_field: student.major_or_field ?? '',
    academic_level: student.academic_level ?? '',
    weekly_hours: String(student.weekly_hours ?? 0),
    primary_focus: String(goals.primary_focus ?? ''),
    target_course: String(goals.target_course ?? goals.course ?? ''),
    career_goal: String(goals.career_goal ?? goals.career_goals ?? ''),
    interests: listToText(student.interests),
    preferred_formats: listToText(student.preferred_formats),
    learning_style_summary: String(llm.learning_style_summary ?? llm['Learning Style'] ?? ''),
    subject_confidence: String(llm.subject_confidence ?? ''),
    notes: String(llm.notes ?? ''),
  };
}

function EditableProfileForm({
  student,
  saving,
  onCancel,
  onSave,
}: {
  student: StudentProfile;
  saving: boolean;
  onCancel: () => void;
  onSave: (payload: StudentProfileUpdate) => Promise<void>;
}) {
  const [form, setForm] = useState<ProfileFormState>(() => initialFormState(student));
  const [styleEdited, setStyleEdited] = useState(false);

  const setField = (field: keyof ProfileFormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const setPreferredFormats = (value: string) => {
    setForm((current) => ({
      ...current,
      preferred_formats: value,
      learning_style_summary: styleEdited
        ? current.learning_style_summary
        : suggestedLearningStyle(value, current.subject_confidence),
    }));
  };

  const togglePreferredFormat = (format: string) => {
    const current = textToList(form.preferred_formats);
    const exists = current.some((item) => item.toLowerCase() === format.toLowerCase());
    const next = exists
      ? current.filter((item) => item.toLowerCase() !== format.toLowerCase())
      : [...current, format];
    setPreferredFormats(listToText(next));
  };

  const setSubjectConfidence = (value: string) => {
    setForm((current) => ({
      ...current,
      subject_confidence: value,
      learning_style_summary: styleEdited
        ? current.learning_style_summary
        : suggestedLearningStyle(current.preferred_formats, value),
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const weeklyHours = Number.parseInt(form.weekly_hours, 10);
    await onSave({
      name: form.name.trim(),
      major_or_field: form.major_or_field.trim(),
      academic_level: form.academic_level.trim(),
      weekly_hours: Number.isFinite(weeklyHours) ? Math.max(0, weeklyHours) : 0,
      interests: textToList(form.interests),
      preferred_formats: textToList(form.preferred_formats),
      learning_goals: {
        primary_focus: form.primary_focus.trim(),
        target_course: form.target_course.trim(),
        career_goal: form.career_goal.trim(),
      },
      llm_profile: {
        learning_style_summary: form.learning_style_summary.trim(),
        subject_confidence: form.subject_confidence.trim(),
        notes: form.notes.trim(),
      },
    });
  };

  const inputClass =
    'w-full rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:opacity-50';
  const labelClass = 'text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400';
  const selectedFormats = textToList(form.preferred_formats);

  return (
    <form onSubmit={handleSubmit} className="max-w-5xl mx-auto space-y-6">
      <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 border-2 border-industrial/40 dark:border-industrial/30 shadow-soft p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <div>
            <h2 className="text-2xl font-bold font-display text-slate-900 dark:text-white">Edit learner profile</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Updates keep the same structure used by roadmap and lesson personalization.</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={saving}
              className="rounded-xl border-2 border-slate-200 dark:border-slate-600 px-4 py-2 text-sm font-semibold text-slate-600 dark:text-slate-300 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.name.trim()}
              className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="space-y-1.5">
            <span className={labelClass}>Name</span>
            <input className={inputClass} value={form.name} onChange={(e) => setField('name', e.target.value)} placeholder="Charles Nguyen" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Major / field</span>
            <input className={inputClass} value={form.major_or_field} onChange={(e) => setField('major_or_field', e.target.value)} placeholder="Accounting, Business, Finance + Data Science" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Academic level</span>
            <select className={inputClass} value={form.academic_level} onChange={(e) => setField('academic_level', e.target.value)}>
              <option value="">Select level</option>
              {ACADEMIC_LEVEL_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Weekly hours</span>
            <input className={inputClass} type="number" min="0" value={form.weekly_hours} onChange={(e) => setField('weekly_hours', e.target.value)} placeholder="8" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Primary focus</span>
            <input className={inputClass} value={form.primary_focus} onChange={(e) => setField('primary_focus', e.target.value)} placeholder="Build accounting foundations" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Target course</span>
            <input className={inputClass} value={form.target_course} onChange={(e) => setField('target_course', e.target.value)} placeholder="Financial and Managerial Accounting" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Career goal</span>
            <input className={inputClass} value={form.career_goal} onChange={(e) => setField('career_goal', e.target.value)} placeholder="Prepare for CPA-style reporting work" />
          </label>
          <label className="space-y-1.5">
            <span className={labelClass}>Subject confidence</span>
            <select className={inputClass} value={form.subject_confidence} onChange={(e) => setSubjectConfidence(e.target.value)}>
              <option value="">Select confidence</option>
              {SUBJECT_CONFIDENCE_OPTIONS.map((option) => (
                <option key={option} value={option}>{option.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </label>
          <label className="space-y-1.5 md:col-span-2">
            <span className={labelClass}>Interests</span>
            <input className={inputClass} value={form.interests} onChange={(e) => setField('interests', e.target.value)} placeholder="python, finance, CPA prep" />
          </label>
          <label className="space-y-1.5 md:col-span-2">
            <span className={labelClass}>Preferred formats</span>
            <div className="flex flex-wrap gap-2 rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3">
              {PREFERRED_FORMAT_OPTIONS.map((format) => {
                const selected = selectedFormats.some((item) => item.toLowerCase() === format.toLowerCase());
                return (
                  <button
                    key={format}
                    type="button"
                    onClick={() => togglePreferredFormat(format)}
                    className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
                      selected
                        ? 'border-primary bg-primary text-white'
                        : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-primary/50'
                    }`}
                    aria-pressed={selected}
                  >
                    {format}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-slate-400">Choose one or more formats. These directly control lesson activities like videos and flashcards.</p>
          </label>
          <label className="space-y-1.5 md:col-span-2">
            <span className={labelClass}>Learning style summary</span>
            <textarea
              className={inputClass}
              rows={3}
              value={form.learning_style_summary}
              onChange={(e) => {
                setStyleEdited(true);
                setField('learning_style_summary', e.target.value);
              }}
              placeholder="Prefers worked examples and MCQs; wants fewer flashcards."
            />
          </label>
          <label className="space-y-1.5 md:col-span-2">
            <span className={labelClass}>Notes</span>
            <textarea className={inputClass} rows={3} value={form.notes} onChange={(e) => setField('notes', e.target.value)} placeholder="Use startup finance examples and avoid flashcards unless requested." />
          </label>
        </div>
      </div>
    </form>
  );
}

export default function ProfilePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { studentId } = usePersona();
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchStudent(studentId)
      .then((student) => {
        if (!cancelled) {
          setStudent(student);
          setProfile(mapStudentProfile(student));
          setEditing(false);
        }
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

  async function handleSave(payload: StudentProfileUpdate) {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateStudent(studentId, payload);
      setStudent(updated);
      setProfile(mapStudentProfile(updated));
      setEditing(false);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

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
        ) : editing && student ? (
          <EditableProfileForm
            student={student}
            saving={saving}
            onCancel={() => setEditing(false)}
            onSave={handleSave}
          />
        ) : profile ? (
          <LearnerProfileCard profile={profile} onEdit={() => setEditing(true)} />
        ) : (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
            No profile data found.
          </div>
        )}
      </div>
    </AppLayout>
  );
}
