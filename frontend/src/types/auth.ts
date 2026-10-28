export type UserRole = 'ADMIN' | 'TEACHER' | 'STUDENT'

export interface User {
  id: string
  username: string
  displayName: string
  roles: UserRole[]
}

export interface LoginResult {
  accessToken: string
  tokenType: string
}
