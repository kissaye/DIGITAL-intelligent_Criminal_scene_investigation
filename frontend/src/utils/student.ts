import type { StudentTaskStatus } from '@/types/student'
export const taskStatus = (status: StudentTaskStatus) => ({ CLOSED: ['已关闭', 'info'], NOT_STARTED: ['未开始', 'info'], IN_PROGRESS: ['进行中', 'primary'], EXPIRED: ['已截止', 'danger'], SUBMITTED: ['已提交', 'success'] }[status] as [string, 'info' | 'primary' | 'danger' | 'success'])
export const displayTime = (time: string | null) => time ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(time)) : '-'
