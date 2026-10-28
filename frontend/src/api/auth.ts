import http, { responseData } from '@/api/http'
import type { LoginResult, User, UserRole } from '@/types/auth'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'

function mockUser(username: string): User {
  const normalized = username.trim().toLowerCase()
  const role: UserRole = normalized.includes('admin') ? 'ADMIN' : normalized.includes('teacher') ? 'TEACHER' : 'STUDENT'
  return { id: `mock-${normalized}`, username, displayName: username, roles: [role] }
}

function wait(milliseconds = 350) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

export async function login(username: string, password: string): Promise<LoginResult> {
  if (useMock) {
    await wait()
    if (!username.trim() || !password) throw new Error('用户名和密码不能为空')
    return { accessToken: `mock-token-${btoa(username)}`, tokenType: 'bearer' }
  }
  const response = await http.post('/api/v1/auth/login', { username, password })
  return responseData<LoginResult>(response)
}

export async function getCurrentUser(): Promise<User> {
  if (useMock) {
    await wait(180)
    const token = localStorage.getItem('dici.access-token')
    if (!token?.startsWith('mock-token-')) throw new Error('Mock 登录状态不存在')
    return mockUser(atob(token.slice('mock-token-'.length)))
  }
  const response = await http.get('/api/v1/auth/me')
  return responseData<User>(response)
}
