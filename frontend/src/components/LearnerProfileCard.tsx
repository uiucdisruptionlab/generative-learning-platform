import React from 'react';

export interface LearnerProfile {
  id: string;
  name: string;
  major_or_field: string;
  learning_goals: string[] | null;
  interests: string[] | null;
  academic_level: string | number;
  weekly_hours: number;
  preferred_formats: string[] | null;
  llm_profile: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

interface LearnerProfileCardProps {
  profile: LearnerProfile;
  onEdit?: () => void;
}

const LearnerProfileCard: React.FC<LearnerProfileCardProps> = ({ profile, onEdit }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'Not available';
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getAcademicLevelLabel = (level: string | number) => {
    if (typeof level === 'number') {
      const labels = ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate'];
      return labels[level - 1] || `Year ${level}`;
    }
    return level;
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Card with Avatar and Basic Info */}
      <div className="rounded-2xl bg-gradient-to-br from-white via-storm-300/35 to-white dark:from-slate-900 dark:via-slate-800/50 dark:to-slate-900 border-2 border-industrial/40 dark:border-industrial/35 shadow-soft p-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          {/* Avatar */}
          <div className="relative">
            <div className="size-24 rounded-full bg-gradient-to-br from-primary to-canvas-green flex items-center justify-center text-white text-3xl font-bold font-display shadow-lg ring-4 ring-white dark:ring-slate-900">
              {getInitials(profile.name)}
            </div>
            <div className="absolute -bottom-1 -right-1 size-8 rounded-full bg-canvas-green border-4 border-white dark:border-slate-900 flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-sm">verified</span>
            </div>
          </div>

          {/* Basic Info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <h1 className="text-3xl font-extrabold font-display text-slate-900 dark:text-white">
                {profile.name}
              </h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 dark:bg-primary/20 px-3 py-1 text-xs font-bold text-primary border border-primary/20">
                <span className="material-symbols-outlined text-sm">school</span>
                {getAcademicLevelLabel(profile.academic_level)}
              </span>
            </div>
            <p className="text-lg text-slate-600 dark:text-slate-300 mb-3">
              <span className="material-symbols-outlined text-base align-middle mr-1">menu_book</span>
              {profile.major_or_field}
            </p>
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-base">badge</span>
                ID: {profile.id.slice(0, 8)}
              </span>
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-base">calendar_today</span>
                Joined {formatDate(profile.created_at)}
              </span>
            </div>
          </div>

          {/* Edit Button */}
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary-light text-white px-4 py-2.5 text-sm font-bold shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
            >
              <span className="material-symbols-outlined text-lg">edit</span>
              Edit Profile
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Learning Goals */}
        <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-industrial/40 dark:border-industrial/30 shadow-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-storm-300/60 dark:bg-storm-700/25 text-primary">
              <span className="material-symbols-outlined">target</span>
            </div>
            <h2 className="text-xl font-bold font-display text-slate-900 dark:text-white">
              Learning Goals
            </h2>
          </div>
          <div className="space-y-2">
            {profile.learning_goals && profile.learning_goals.length > 0 ? (
              profile.learning_goals.map((goal, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-3 rounded-xl bg-storm-300/45 dark:bg-storm-700/20 border border-industrial/35 dark:border-industrial/25"
                >
                  <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                  <p className="text-sm text-slate-700 dark:text-slate-300 flex-1">{goal}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400 italic">No learning goals set yet</p>
            )}
          </div>
        </div>

        {/* Weekly Commitment — hidden when no hours collected yet */}
        <div className={`rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-amber-200/50 dark:border-amber-800/30 shadow-soft p-6 ${profile.weekly_hours === 0 ? 'opacity-40' : ''}`}>
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-900/30 text-secondary">
              <span className="material-symbols-outlined">schedule</span>
            </div>
            <h2 className="text-xl font-bold font-display text-slate-900 dark:text-white">
              Weekly Commitment
            </h2>
          </div>
          <div className="space-y-4">
            <div className="flex items-end gap-2">
              <span className="text-5xl font-extrabold font-display text-secondary">
                {profile.weekly_hours}
              </span>
              <span className="text-xl font-bold text-slate-500 dark:text-slate-400 mb-2">
                hours/week
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold uppercase text-slate-500 dark:text-slate-400">
                <span>Time Allocation</span>
                <span className="text-secondary">{Math.round((profile.weekly_hours / 168) * 100)}% of week</span>
              </div>
              <div className="h-3 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-secondary to-amber-500"
                  style={{ width: `${Math.min((profile.weekly_hours / 40) * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {profile.weekly_hours < 5 && "Light commitment - perfect for busy schedules"}
                {profile.weekly_hours >= 5 && profile.weekly_hours < 15 && "Moderate pace - balanced learning"}
                {profile.weekly_hours >= 15 && profile.weekly_hours < 25 && "Intensive learning - strong dedication"}
                {profile.weekly_hours >= 25 && "Full-time commitment - maximum progress"}
              </p>
            </div>
          </div>
        </div>

        {/* Interests */}
        <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-arches/40 dark:border-arches/25 shadow-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-soft-teal dark:bg-patina/15 text-canvas-green">
              <span className="material-symbols-outlined">interests</span>
            </div>
            <h2 className="text-xl font-bold font-display text-slate-900 dark:text-white">
              Interests
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.interests && profile.interests.length > 0 ? (
              profile.interests.map((interest, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1.5 rounded-full bg-soft-teal dark:bg-patina/15 px-3 py-1.5 text-sm font-medium text-canvas-green border border-arches/35 dark:border-arches/20"
                >
                  <span className="material-symbols-outlined text-base">star</span>
                  {interest}
                </span>
              ))
            ) : (
              <p className="text-sm text-slate-400 italic">No interests specified yet</p>
            )}
          </div>
        </div>

        {/* Preferred Learning Formats */}
        <div className="rounded-2xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-2 border-orange-200/50 dark:border-orange-800/30 shadow-soft p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-50 dark:bg-orange-900/30 text-accent">
              <span className="material-symbols-outlined">format_list_bulleted</span>
            </div>
            <h2 className="text-xl font-bold font-display text-slate-900 dark:text-white">
              Preferred Formats
            </h2>
          </div>
          <div className="space-y-2">
            {profile.preferred_formats && profile.preferred_formats.length > 0 ? (
              profile.preferred_formats.map((format, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-xl bg-orange-50/50 dark:bg-orange-900/20 border border-orange-200/50 dark:border-orange-800/30"
                >
                  <span className="material-symbols-outlined text-accent">
                    {format.toLowerCase().includes('video') ? 'play_circle' :
                     format.toLowerCase().includes('text') || format.toLowerCase().includes('reading') ? 'article' :
                     format.toLowerCase().includes('interactive') || format.toLowerCase().includes('practice') ? 'touch_app' :
                     format.toLowerCase().includes('audio') || format.toLowerCase().includes('podcast') ? 'headphones' :
                     'check_box'}
                  </span>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{format}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400 italic">No format preferences specified</p>
            )}
          </div>
        </div>
      </div>

      {/* AI Learning Insights */}
      {profile.llm_profile && Object.keys(profile.llm_profile).length > 0 && (
        <div className="rounded-2xl bg-gradient-to-br from-white via-purple-50/20 to-white dark:from-slate-900 dark:via-purple-900/10 dark:to-slate-900 border-2 border-purple-200/50 dark:border-purple-800/30 shadow-soft p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
              <span className="material-symbols-outlined">psychology</span>
            </div>
            <h2 className="text-xl font-bold font-display text-slate-900 dark:text-white">
              AI Learning Insights
            </h2>
          </div>

          {/* Learning Style — full-width paragraph */}
          {profile.llm_profile['Learning Style'] && (
            <div className="mb-4 p-4 rounded-xl bg-purple-50/60 dark:bg-purple-900/25 border border-purple-200/60 dark:border-purple-800/40">
              <p className="text-xs font-bold uppercase tracking-widest text-purple-600 dark:text-purple-400 mb-2">
                Learning Style
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                {String(profile.llm_profile['Learning Style'])}
              </p>
            </div>
          )}

          {/* Remaining insights — compact grid */}
          {Object.entries(profile.llm_profile).filter(([key]) => key !== 'Learning Style').length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(profile.llm_profile)
                .filter(([key]) => key !== 'Learning Style')
                .map(([key, value]) => (
                  <div
                    key={key}
                    className="p-4 rounded-xl bg-purple-50/50 dark:bg-purple-900/20 border border-purple-200/50 dark:border-purple-800/30"
                  >
                    <p className="text-xs font-bold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-1">
                      {key}
                    </p>
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </p>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Last Updated */}
      <div className="text-center text-xs text-slate-400">
        Last updated: {formatDate(profile.updated_at)}
      </div>
    </div>
  );
};

export default LearnerProfileCard;
