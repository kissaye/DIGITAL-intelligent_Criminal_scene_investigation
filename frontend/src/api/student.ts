import http, { responseData } from '@/api/http'
import type { DraftResponse, StudentDraftPayload, StudentTask, StudentWorkspace, Submission } from '@/types/student'
import type { Annotation, Measurement } from '@/types/viewer'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const key = (suffix: string) => `dici.mock-student-${suffix}`
const wait = (ms = 180) => new Promise((resolve) => window.setTimeout(resolve, ms))
const emptyWorkspace = (): StudentWorkspace => ({ manifestUrl: '', draft: { overview: '', process: '', evidenceDescription: '', preliminaryConclusion: '' }, annotations: [], measurements: [], submitted: false, submittedAt: null, submissionVersion: null })
interface WorkspaceResponse { task: StudentTask; draft: DraftResponse | null; viewerConfig: { versionId: string; manifestUrl: string } }
function toWorkspace(response: WorkspaceResponse): StudentWorkspace { const draft = response.draft; return { manifestUrl: response.viewerConfig.manifestUrl, draft: draft?.reportContent || emptyWorkspace().draft, annotations: draft?.marks || [], measurements: draft?.measurements || [], submitted: draft?.status === 'SUBMITTED', submittedAt: draft?.submittedAt || null, submissionVersion: draft?.version || null } }
function toPayload(workspace: StudentWorkspace): StudentDraftPayload { return { reportContent: workspace.draft, marks: workspace.annotations, measurements: workspace.measurements } }
export async function getSubmittedWork(submissionId: string): Promise<DraftResponse> {
  if (!useMock) return responseData<DraftResponse>(await http.get(`/api/v1/student/submissions/${submissionId}`))
  const t = mockTasks().find(t => t.submissionId === submissionId)
  if (!t) throw new Error('提交不存在')
  const w = mockWorkspace(t.id)
  return { id: submissionId, status: 'SUBMITTED', reportContent: w.draft, marks: w.annotations, measurements: w.measurements, submittedAt: w.submittedAt, version: w.submissionVersion }
}
function applyDraftResponse(workspace: StudentWorkspace, draft: DraftResponse): StudentWorkspace { return { ...workspace, draft: draft.reportContent, annotations: draft.marks, measurements: draft.measurements, submitted: draft.status === 'SUBMITTED', submittedAt: draft.submittedAt, submissionVersion: draft.version } }
function mockTasks(): StudentTask[] { const raw = localStorage.getItem(key('tasks')); if (raw) return JSON.parse(raw) as StudentTask[]; const tasks: StudentTask[] = [{ id: 'mock-task-001', name: '住宅现场勘查实训', caseName: '教学演示案例', instructions: '完成现场观察、标记与勘验笔录。', caseVersionId: 'mock-version-001', startAt: '2026-10-01T08:00:00+08:00', dueAt: '2026-12-31T23:59:59+08:00', status: 'IN_PROGRESS', allowLate: false, submissionId: null, submittedAt: null, submissionVersion: null }]; localStorage.setItem(key('tasks'), JSON.stringify(tasks)); return tasks }
function mockWorkspace(taskId: string): StudentWorkspace { const raw = localStorage.getItem(key(`workspace-${taskId}`)); if (raw) return JSON.parse(raw); const workspace = emptyWorkspace(); localStorage.setItem(key(`workspace-${taskId}`), JSON.stringify(workspace)); return workspace }
function saveWorkspace(taskId: string, value: StudentWorkspace) { localStorage.setItem(key(`workspace-${taskId}`), JSON.stringify(value)) }
function task(taskId: string) { const item = mockTasks().find((value) => value.id === taskId); if (!item) throw new Error('实训任务不存在'); return item }

export async function getStudentTasks(): Promise<StudentTask[]> { if (!useMock) return responseData<StudentTask[]>(await http.get('/api/v1/student/tasks')); await wait(); return mockTasks() }
export async function getStudentTask(taskId: string): Promise<StudentTask> { if (!useMock) return responseData<StudentTask>(await http.get(`/api/v1/student/tasks/${taskId}`)); await wait(); return task(taskId) }
export async function getStudentWorkspace(taskId: string): Promise<StudentWorkspace> { if (!useMock) return toWorkspace(responseData<WorkspaceResponse>(await http.get(`/api/v1/student/tasks/${taskId}/workspace`))); await wait(); return mockWorkspace(taskId) }
export async function saveStudentDraft(taskId: string, workspace: StudentWorkspace): Promise<StudentWorkspace> { if (!useMock) { const response = responseData<DraftResponse>(await http.put(`/api/v1/student/tasks/${taskId}/draft`, toPayload(workspace))); return applyDraftResponse(workspace, response) } await wait(280); saveWorkspace(taskId, workspace); return workspace }
export async function submitStudentTask(taskId: string, workspace: StudentWorkspace): Promise<Submission> { if (!useMock) { const response = responseData<DraftResponse>(await http.post(`/api/v1/student/tasks/${taskId}/submissions`, toPayload(workspace))); return { id: response.id, submittedAt: response.submittedAt || new Date().toISOString(), version: response.version || '' } } await wait(350); const submittedAt = new Date().toISOString(); workspace.submitted = true; workspace.submittedAt = submittedAt; workspace.submissionVersion = 'v1'; saveWorkspace(taskId, workspace); const tasks = mockTasks(); const item = task(taskId); item.status = 'SUBMITTED'; item.submittedAt = submittedAt; item.submissionVersion = 'v1'; item.submissionId = `mock-submission-${Date.now()}`; localStorage.setItem(key('tasks'), JSON.stringify(tasks)); return { id: item.submissionId, submittedAt, version: 'v1' } }
export async function getStudentSubmission(submissionId: string): Promise<Submission> { if (!useMock) return responseData<Submission>(await http.get(`/api/v1/student/submissions/${submissionId}`)); await wait(); const item = mockTasks().find((value) => value.submissionId === submissionId); if (!item?.submittedAt || !item.submissionVersion) throw new Error('提交记录不存在'); return { id: submissionId, submittedAt: item.submittedAt, version: item.submissionVersion } }
