import type { UserRole } from '@/types/auth'

export const TOKEN_KEY = 'dici.access-token'
export const TOKEN_TYPE_KEY = 'dici.token-type'

export function homeRouteForRoles(roles: UserRole[] = []) {
  if (roles.includes('ADMIN')) return '/admin'
  if (roles.includes('TEACHER')) return '/teacher'
  return '/student'
}

export function roleLabel(roles: UserRole[] = []) {
  const labels: Record<UserRole, string> = { ADMIN: '管理员', TEACHER: '教师', STUDENT: '学生' }
  return roles.map((role) => labels[role]).join('、') || '未分配角色'
}
