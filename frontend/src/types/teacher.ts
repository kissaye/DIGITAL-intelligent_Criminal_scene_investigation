import type {AreaMeasurement} from '@/types/area'
import type { Annotation, Measurement } from '@/types/viewer'
import type { RecordDraft } from '@/types/student'

export interface TeacherStudent { id: string | number; username: string; displayName: string }
export interface Course { id: string; title: string; description: string; classCount?: number }
export interface TeachingClass { id: string; courseId: string; name: string; memberIds: Array<string | number>; studentCount: number }
export interface ReadyCaseVersion { id: string; caseName: string; internalCode: string; createdAt: string }
export interface TeacherTask { id: string; classId: string; className: string; title: string; instructions: string; caseVersionId: string; caseName: string; startAt: string | null; dueAt: string | null; allowLate: boolean; assignedCount: number; submittedCount: number }
export interface TeacherSubmission { areaMeasurements?: AreaMeasurement[]; id: string; studentId: string; studentName: string; status: 'DRAFT' | 'SUBMITTED'; submittedAt: string | null; score: number | null; gradedAt: string | null; feedback: string | null; reportContent?: RecordDraft; marks?: Annotation[]; measurements?: Measurement[] }
export interface CreateTeacherTask { classId: string; title: string; instructions: string; caseVersionId: string; startAt: string | null; dueAt: string | null; allowLate: boolean; reportTemplate: Record<string, unknown> }
