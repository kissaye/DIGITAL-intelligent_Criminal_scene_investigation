import { defineStore } from 'pinia'
import { getCurrentUser, login as requestLogin } from '@/api/auth'
import type { User } from '@/types/auth'
import { TOKEN_KEY, TOKEN_TYPE_KEY } from '@/utils/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: null as User | null,
    restored: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
  },
  actions: {
    async login(username: string, password: string) {
      const result = await requestLogin(username, password)
      this.token = result.accessToken
      localStorage.setItem(TOKEN_KEY, result.accessToken)
      localStorage.setItem(TOKEN_TYPE_KEY, result.tokenType)
      this.user = await getCurrentUser()
      this.restored = true
    },
    async restore() {
      if (this.restored) return
      if (!this.token) {
        this.restored = true
        return
      }
      try {
        this.user = await getCurrentUser()
      } catch {
        this.clear()
      } finally {
        this.restored = true
      }
    },
    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(TOKEN_TYPE_KEY)
    },
  },
})
