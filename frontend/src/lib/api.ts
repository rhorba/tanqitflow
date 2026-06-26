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

// Map / GeoJSON helpers
export interface DmaFeatureProperties {
  id: string
  code: string
  name: string
  zone: string | null
  pipe_length_km: number | null
  connection_count: number | null
  nrw_pct: number | null
  nrw_m3: number | null
  siv_m3: number | null
  scv_m3: number | null
  flag_level: 'normal' | 'warning' | 'critical'
}

export interface DmaGeoJSON {
  type: 'FeatureCollection'
  features: Array<GeoJSON.Feature<GeoJSON.Geometry | null, DmaFeatureProperties>>
  heat_points: [number, number, number][]
}

export const mapApi = {
  getGeoJSON: () => api.get<DmaGeoJSON>('/dmas/geojson'),
}

// DMA table + detail helpers
export interface DmaTableRow {
  id: string
  code: string
  name: string
  zone: string | null
  pipe_length_km: number | null
  connection_count: number | null
  siv_m3: number | null
  scv_m3: number | null
  nrw_m3: number | null
  nrw_pct: number | null
  flag_level: 'normal' | 'warning' | 'critical'
  confidence_score: number
  alert_type: string
  has_leak_flag: boolean
}

export interface DmaBalancePeriod {
  id: string
  dma_code: string
  period_start: string
  period_end: string
  siv_m3: number
  scv_m3: number
  nrw_m3: number
  nrw_pct: number
  leakage_index: number | null
  flag_level: 'normal' | 'warning' | 'critical'
}

export const dmaApi = {
  getTable: (page = 1, pageSize = 50) =>
    api.get<{ data: DmaTableRow[]; meta: { page: number; page_size: number; total: number } }>(
      `/dmas/table?page=${page}&page_size=${pageSize}`
    ),

  getById: (id: string) =>
    api.get<{
      id: string; code: string; name: string; zone: string | null
      pipe_length_km: number | null; connection_count: number | null
      is_active: boolean
    }>(`/dmas/${id}`),

  getBalanceHistory: (id: string, months = 12) =>
    api.get<{ data: DmaBalancePeriod[]; dma_code: string; dma_name: string }>(
      `/dmas/${id}/balance?months=${months}`
    ),
}

// Worklist helpers
export interface WorklistItem {
  id: string
  dma_code: string
  dma_name: string | null
  rank: number
  estimated_loss_m3_per_month: number | null
  savings_mad_est: number | null
  confidence_score: number
  alert_type: string
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'DEFERRED'
  generated_at: string
  updated_at: string
}

export const worklistApi = {
  list: (page = 1, size = 20, status?: string) =>
    api.get<{ data: WorklistItem[]; total: number; page: number; size: number }>(
      `/worklist?page=${page}&size=${size}${status ? `&status=${status}` : ''}`
    ),

  generate: (waterCost = 16.0) =>
    api.post<{ generated: number; water_cost_mad_per_m3: number }>('/worklist/generate', {
      water_cost_mad_per_m3: waterCost,
    }),

  updateStatus: (id: string, status: WorklistItem['status']) =>
    api.patch<WorklistItem>(`/worklist/${id}`, { status }),

  exportCsvUrl: () => '/api/v1/worklist/export?format=csv',
}

// Leak indicator helpers
export interface LeakIndicator {
  id: string
  dma_code: string
  indicator_date: string
  mnf_m3h: number | null
  baseline_m3h: number | null
  mnf_flag: boolean
  max_zscore: number | null
  zscore_flag: boolean
  if_anomaly_score: number | null
  if_flag: boolean
  confidence_score: number
  alert_type: string
  computed_at: string
}

export const leakApi = {
  getIndicators: (dmaCode: string, page = 1, size = 30) =>
    api.get<{ data: LeakIndicator[]; total: number; page: number; size: number }>(
      `/leak/indicators?dma_code=${dmaCode}&page=${page}&size=${size}`
    ),

  getAnomalies: (dmaCode: string, page = 1, size = 50) =>
    api.get<{ data: Array<{ id: string; dma_code: string; event_time: string; metric: string; value: number; zscore: number }>; total: number }>(
      `/leak/anomalies?dma_code=${dmaCode}&page=${page}&size=${size}`
    ),
}

// User "me" helpers
export interface UserMe {
  id: string
  email: string
  role: string
  is_active: boolean
  language_pref: 'fr' | 'ar'
  created_at: string
  last_login_at: string | null
}

export const userApi = {
  getMe: () => api.get<UserMe>('/users/me'),
  updateMe: (body: { language_pref?: 'fr' | 'ar' }) =>
    api.patch<UserMe>('/users/me', body),
}

// Report helpers
export const reportApi = {
  request: (fromDate: string, toDate: string, lang: 'fr' | 'ar') =>
    api.post<{ task_id: string; report_id: string }>('/reports/water-balance', {
      from_date: fromDate,
      to_date: toDate,
      lang,
    }),
  pollDownload: (taskId: string) =>
    api.get<{ status: string; url?: string; size_bytes?: number }>(
      `/reports/download/${taskId}`
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
