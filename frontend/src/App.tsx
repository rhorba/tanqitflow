import { useEffect } from 'react'
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import Header from './components/layout/Header'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import DashboardPage from './pages/DashboardPage'
import IngestionPage from './pages/IngestionPage'
import MapPage from './pages/MapPage'
import DmasPage from './pages/DmasPage'
import DmaDetailPage from './pages/DmaDetailPage'
import WorklistPage from './pages/WorklistPage'
import ReportsPage from './pages/ReportsPage'
import { useAuthStore } from './stores/authStore'
import { userApi } from './lib/api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
    },
  },
})

function AppShell() {
  const { i18n, t } = useTranslation()
  const token = useAuthStore((s) => s.accessToken)
  const setLanguagePref = useAuthStore((s) => s.setLanguagePref)

  // Sync RTL/LTR and page <title>
  useEffect(() => {
    const dir = i18n.language === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.setAttribute('dir', dir)
    document.documentElement.setAttribute('lang', i18n.language)
    document.title = t('app.name')
  }, [i18n.language, t])

  // On login, load language_pref from API and apply it
  useEffect(() => {
    if (!token) return
    userApi.getMe()
      .then(({ data }) => {
        const pref = data.language_pref as 'fr' | 'ar'
        if (pref && pref !== i18n.language) {
          i18n.changeLanguage(pref)
        }
        setLanguagePref(pref ?? 'fr')
      })
      .catch(() => {})
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      {/* Public routes — no Header */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      {/* Protected routes — with Header */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div className="min-h-screen bg-gray-50">
              <Header />
              <main className="container mx-auto px-4 py-8">
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route path="/dmas" element={<DmasPage />} />
                  <Route path="/dmas/:id" element={<DmaDetailPage />} />
                  <Route path="/worklist" element={<WorklistPage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/ingestion" element={<IngestionPage />} />
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </main>
            </div>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
