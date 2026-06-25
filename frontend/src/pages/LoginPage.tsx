import { useState, FormEvent } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'

export default function LoginPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const from = (location.state as { from?: Location })?.from?.pathname ?? '/dashboard'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      setAuth(data.access_token)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const status = (err as { response?: { status: number } })?.response?.status
      if (status === 429) {
        setError(t('auth.too_many_attempts'))
      } else {
        setError(t('auth.invalid_credentials'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-teal-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo / brand */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-teal-700">{t('app.name')}</h1>
          <p className="text-gray-500 mt-1 text-sm">{t('app.tagline')}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">{t('auth.sign_in')}</h2>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent text-sm"
                dir="ltr"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  {t('auth.password')}
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-teal-600 hover:text-teal-800 hover:underline"
                >
                  {t('auth.forgot_password')}
                </Link>
              </div>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent text-sm"
                dir="ltr"
              />
            </div>

            {/* Error */}
            {error && (
              <p role="alert" className="text-red-600 text-sm text-center">
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
            >
              {loading ? t('common.loading') : t('auth.sign_in')}
            </button>
          </form>
        </div>

        {/* Language switcher */}
        <div className="flex justify-center gap-4 mt-6 text-sm">
          <button
            onClick={() => i18n.changeLanguage('fr')}
            className={`px-3 py-1 rounded ${i18n.language === 'fr' ? 'bg-teal-100 text-teal-700 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Français
          </button>
          <button
            onClick={() => i18n.changeLanguage('ar')}
            className={`px-3 py-1 rounded ${i18n.language === 'ar' ? 'bg-teal-100 text-teal-700 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
          >
            العربية
          </button>
        </div>
      </div>
    </div>
  )
}
