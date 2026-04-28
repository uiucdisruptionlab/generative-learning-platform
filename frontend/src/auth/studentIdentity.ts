export const PERSONA_STUDENT_IDS: Record<string, string> = {
  alice: 'a0000001-0000-4000-8000-000000000001',
  bob: 'b0000002-0000-4000-8000-000000000002',
  charles: 'c0000003-0000-4000-8000-000000000003',
  demo: 'c0000003-0000-4000-8000-000000000003',
}

export function studentIdForPersona(persona: string): string {
  return PERSONA_STUDENT_IDS[persona] ?? persona
}
