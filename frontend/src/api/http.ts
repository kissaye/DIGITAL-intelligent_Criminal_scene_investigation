import axios, { type AxiosResponse } from 'axios'
import { TOKEN_KEY, TOKEN_TYPE_KEY } from '@/utils/auth'

export interface ApiResponse<T> {
  code?: number
  message?: string
  data: T
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  withCredentials: true,
  timeout: 15_000,
})

http.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem(TOKEN_KEY)
  if (accessToken) {
    const tokenType = localStorage.getItem(TOKEN_TYPE_KEY) || 'Bearer'
    config.headers.Authorization = `${tokenType} ${accessToken}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(TOKEN_TYPE_KEY)
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export function responseData<T>(response: AxiosResponse<ApiResponse<T> | T>): T {
  const body = response.data
  if (body && typeof body === 'object' && 'data' in body) return (body as ApiResponse<T>).data
  return body as T
}

export default http
