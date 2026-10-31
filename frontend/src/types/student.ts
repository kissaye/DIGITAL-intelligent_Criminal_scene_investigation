import type { Annotation, Measurement } from '@/types/viewer'

export type StudentTaskStatus = 'CLOSED' | 'NOT_STARTED' | 'IN_PROGRESS' | 'EXPIRED' | 'SUBMITTED'
export interface RecordDraft { overview: string; process: string; evidenceDescription: string; preliminaryConclusion: string }
export interface StudentTask { id: string; name: string; caseName: string; instructions: string; caseVersionId: string; startAt: string | null; dueAt: string | null; status: StudentTaskStatus; allowLate: boolean; submissionId: string | null; submittedAt: string | null; submissionVersion: string | null }
export interface StudentWorkspace { manifestUrl: string; draft: RecordDraft; annotations: Annotation[]; measurements: Measurement[]; submitted: boolean; submittedAt: string | null; submissionVersion: string | null }
export interface Submission { id: string; submittedAt: string; version: string }
export interface StudentDraftPayload { reportContent: RecordDraft; marks: Annotation[]; measurements: Measurement[] }
export interface DraftResponse { id: string; status: string; reportContent: RecordDraft; marks: Annotation[]; measurements: Measurement[]; submittedAt: string | null; version: string | null }
