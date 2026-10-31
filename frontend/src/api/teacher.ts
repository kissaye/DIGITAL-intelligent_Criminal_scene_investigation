import http, { responseData } from '@/api/http'
import type { Course, Grade, Review, Student, SubmissionRow, TaskForm, TeachingClass, TeachingTask } from '@/types/teacher'
import { teacherMock } from './teacherMock'

const base = '/api/v1/teacher'
const mock = import.meta.env.VITE_USE_MOCK !== 'false'
export async function get<T>(path: string): Promise<T> { return mock ? teacherMock<T>('GET',path) : responseData<T>(await http.get(base + path)) }
export async function post<T>(path: string, data: unknown = {}): Promise<T> { return mock ? teacherMock<T>('POST',path,data) : responseData<T>(await http.post(base + path, data)) }
export async function patch<T>(path: string, data: unknown): Promise<T> { return mock ? teacherMock<T>('PATCH',path,data) : responseData<T>(await http.patch(base + path, data)) }
export const courses = () => get<Course[]>('/courses')
export const course = (id: string) => get<Course>(`/courses/${id}`)
export const teachingClass = (id: string) => get<TeachingClass>(`/classes/${id}`)
export const findStudent = (name: string) => get<Student[]>(`/students?username=${encodeURIComponent(name)}`)
export async function removeMember(classId: string, studentId: number) { if(mock) await teacherMock('DELETE',`/classes/${classId}/members/${studentId}`); else await http.delete(`${base}/classes/${classId}/members/${studentId}`) }
export const tasks = (courseId: string, status: string) => get<TeachingTask[]>(`/tasks?courseId=${encodeURIComponent(courseId)}&status=${status}`)
export const task = (id: string) => get<TeachingTask>(`/tasks/${id}`)
export function saveTask(id: string | undefined, form: TaskForm) { const payload = { ...form, rubric: form.rubric.map(({ title, description, maxScore }) => ({ title, description, maxScore })) }; return id ? patch<TeachingTask>(`/tasks/${id}`, payload) : post<TeachingTask>('/tasks', payload) }
export const submissions = (id: string) => get<SubmissionRow[]>(`/tasks/${id}/submissions`)
export const review = (id: string) => get<Review>(`/submissions/${id}`)
export async function saveGrade(id: string, feedback: string, items: Grade['items']) { return responseData<Grade>(await http.put(`${base}/submissions/${id}/grade`, { feedback, items: items.filter(i => i.score !== null && i.score !== undefined) })) }
export function message(error: unknown) { return (error as { response?: { data?: { message?: string } } }).response?.data?.message || (error instanceof Error ? error.message : '操作失败') }
