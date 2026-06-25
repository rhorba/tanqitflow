import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // send httpOnly refresh_token cookie
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

// Transparent token refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve) => {
        refreshQueue.push((token) => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(api(original))
        })
      })
    }

    original._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post<{ access_token: string }>(
        '/api/v1/auth/refresh',
        {},
        { withCredentials: true }
      )
      useAuthStore.getState().setAuth(data.access_token)
      refreshQueue.forEach((cb) => cb(data.access_token))
      refreshQueue = []
      original.headers.Authorization = `Bearer ${data.access_token}`
      return api(original)
    } catch {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  }
)

export default api

// Balance / NRW helpers
export const balanceApi = {
  getSummary: () =>
    api.get<{
      siv_m3: number
      scv_m3: number
      nrw_m3: number
      nrw_pct: number
      flagged_dmas: number
    }>('/balance/summary'),

  getTrend: (months = 12) =>
    api.get<Array<{ month: string; siv_m3: number; nrw_m3: number; nrw_pct: number }>>(
      `/balance/trend?months=${months}`
    ),
}

// Auth-specific helpers
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { email, password }),

  logout: () =>
    api.post('/auth/logout'),

  requestPasswordReset: (email: string) =>
    api.post('/auth/password-reset/request', { email }),

  confirmPasswordReset: (token: string, new_password: string) =>
    api.post('/auth/password-reset/confirm', { token, new_password }),
}
