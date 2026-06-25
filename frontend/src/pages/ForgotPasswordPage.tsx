import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authApi } from '../lib/api'

type Stage = 'request' | 'sent' | 'confirm' | 'done'

export default function ForgotPasswordPage() {
  const { t } = useTranslation()

  const [stage, setStage] = useState<Stage>('request')
  const [email, setEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRequest(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.requestPasswordReset(email)
      setStage('sent')
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError(t('auth.passwords_do_not_match'))
      return
    }
    if (newPassword.length < 8) {
      setError(t('auth.password_too_short'))
      return
    }
    setLoading(true)
    try {
      await authApi.confirmPasswordReset(resetToken, newPassword)
      setStage('done')
    } catch {
      setError(t('auth.reset_token_invalid'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-teal-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-teal-700">{t('app.name')}</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-8">

          {/* Stage: request email */}
          {stage === 'request' && (
            <>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">{t('auth.forgot_password')}</h2>
              <p className="text-sm text-gray-500 mb-6">{t('auth.reset_instructions')}</p>
              <form onSubmit={handleRequest} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    {t('auth.email')}
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
                    dir="ltr"
                  />
                </div>
                {error && <p role="alert" className="text-red-600 text-sm">{error}</p>}
                <button
                  type="submit"
                  disabled={loading || !email}
                  className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition-colors text-sm"
                >
                  {loading ? t('common.loading') : t('auth.send_reset_link')}
                </button>
              </form>
            </>
          )}

          {/* Stage: link sent */}
          {stage === 'sent' && (
            <div className="text-center space-y-4">
              <div className="text-4xl">📧</div>
              <h2 className="text-xl font-semibold text-gray-800">{t('auth.reset_email_sent')}</h2>
              <p className="text-sm text-gray-500">{t('auth.reset_email_description')}</p>
              <button
                onClick={() => setStage('confirm')}
                className="text-sm text-teal-600 hover:underline"
              >
                {t('auth.enter_reset_token')}
              </button>
            </div>
          )}

          {/* Stage: enter token + new password */}
          {stage === 'confirm' && (
            <>
              <h2 className="text-xl font-semibold text-gray-800 mb-6">{t('auth.new_password')}</h2>
              <form onSubmit={handleConfirm} className="space-y-4">
                <div>
                  <label htmlFor="token" className="block text-sm font-medium text-gray-700 mb-1">
                    {t('auth.reset_token')}
                  </label>
                  <input
                    id="token"
                    type="text"
                    required
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-mono"
                    dir="ltr"
                  />
                </div>
                <div>
                  <label htmlFor="newpwd" className="block text-sm font-medium text-gray-700 mb-1">
                    {t('auth.new_password')}
                  </label>
                  <input
                    id="newpwd"
                    type="password"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
                    dir="ltr"
                  />
                </div>
                <div>
                  <label htmlFor="confirmpwd" className="block text-sm font-medium text-gray-700 mb-1">
                    {t('auth.confirm_password')}
                  </label>
                  <input
                    id="confirmpwd"
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
                    dir="ltr"
                  />
                </div>
                {error && <p role="alert" className="text-red-600 text-sm">{error}</p>}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition-colors text-sm"
                >
                  {loading ? t('common.loading') : t('auth.reset_password')}
                </button>
              </form>
            </>
          )}

          {/* Stage: success */}
          {stage === 'done' && (
            <div className="text-center space-y-4">
              <div className="text-4xl">✅</div>
              <h2 className="text-xl font-semibold text-gray-800">{t('auth.password_updated')}</h2>
              <p className="text-sm text-gray-500">{t('auth.password_updated_description')}</p>
            </div>
          )}

          {/* Back to login */}
          {stage !== 'done' && (
            <div className="mt-6 text-center">
              <Link to="/login" className="text-sm text-teal-600 hover:underline">
                ← {t('auth.back_to_login')}
              </Link>
            </div>
          )}
          {stage === 'done' && (
            <div className="mt-6 text-center">
              <Link to="/login" className="inline-block bg-teal-600 text-white text-sm px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors">
                {t('auth.login')}
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
