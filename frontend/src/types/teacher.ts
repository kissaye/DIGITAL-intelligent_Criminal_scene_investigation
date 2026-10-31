export interface Student { id: number; username: string; displayName: string }
export interface Course { id: string; name: string; classes: { id: string; name: string }[] }
export interface TeachingClass { id: string; courseId: string; name: string; members: Student[] }
export interface Rubric { id?: string; title: string; description?: string | null; maxScore: number | string }
export interface TaskForm { courseId: string; title: string; instructions: string; caseVersionId: string; classIds: string[]; startAt: string | null; dueAt: string | null; allowLate: boolean; rubric: Rubric[] }
export interface TeachingTask extends TaskForm { id: string; status: string; assignedCount?: number; submittedCount?: number }
export interface GradeItem { rubricItemId: string; score: number | string | null; comment: string }
export interface Grade { status: string; totalScore: number | string; feedback: string; items: GradeItem[]; publishedAt: string | null; rubric?: Rubric[] }
export interface SubmissionRow { student: Student; submissionId: string | null; status: string; submittedAt: string | null; gradeStatus: string | null; totalScore: number | string | null }
export interface Review { student: Student; task: TeachingTask; submission: { id: string; reportContent: Record<string, unknown>; marks: { id: string; title: string; description: string; geometry: unknown }[]; measurements: { id: string; startPoint: unknown; endPoint: unknown; distance: number }[] }; grade: Grade | null }
