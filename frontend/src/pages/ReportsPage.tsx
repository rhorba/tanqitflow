import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { reportApi } from '../lib/api'

type ReportStatus = 'idle' | 'pending' | 'processing' | 'ready' | 'error'

export default function ReportsPage() {
  const { t, i18n } = useTranslation()
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 12)
    return d.toISOString().slice(0, 10)
  })
  const [toDate, setToDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [lang, setLang] = useState<'fr' | 'ar'>(i18n.language as 'fr' | 'ar')
  const [status, setStatus] = useState<ReportStatus>('idle')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Keep lang in sync with i18n
  useEffect(() => {
    setLang(i18n.language as 'fr' | 'ar')
  }, [i18n.language])

  useEffect(() => {
    if (!taskId || status !== 'pending' && status !== 'processing') return
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await reportApi.pollDownload(taskId)
        if (data.status === 'ready' && data.url) {
          setDownloadUrl(data.url)
          setStatus('ready')
          clearInterval(pollRef.current!)
        } else if (data.status === 'failed') {
          setStatus('error')
          setError(t('reports.generation_failed'))
          clearInterval(pollRef.current!)
        } else {
          setStatus('processing')
        }
      } catch {
        setStatus('error')
        setError(t('common.error'))
        clearInterval(pollRef.current!)
      }
    }, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [taskId, status, t])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setDownloadUrl(null)
    setStatus('pending')
    try {
      const { data } = await reportApi.request(fromDate, toDate, lang)
      setTaskId(data.task_id)
    } catch {
      setStatus('error')
      setError(t('common.error'))
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-800">{t('reports.title')}</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('common.from')}
              </label>
              <input
                type="date"
                value={fromDate}
                max={toDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 outline-none"
                dir="ltr"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('common.to')}
              </label>
              <input
                type="date"
                value={toDate}
                min={fromDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 outline-none"
                dir="ltr"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('reports.language')}
            </label>
            <div className="flex gap-3">
              {(['fr', 'ar'] as const).map((l) => (
                <label key={l} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="lang"
                    value={l}
                    checked={lang === l}
                    onChange={() => setLang(l)}
                    className="accent-blue-600"
                  />
                  <span className="text-sm text-gray-700">
                    {l === 'fr' ? 'Français' : 'العربية'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={status === 'pending' || status === 'processing'}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {status === 'pending' || status === 'processing'
              ? t('reports.generating')
              : t('reports.generate')}
          </button>
        </form>

        {/* Status indicator */}
        {(status === 'pending' || status === 'processing') && (
          <div className="flex items-center gap-3 text-sm text-blue-700">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            {t('reports.generating')}
          </div>
        )}

        {status === 'ready' && downloadUrl && (
          <div className="rounded-lg bg-green-50 border border-green-200 p-4 flex items-center justify-between gap-4">
            <span className="text-sm font-medium text-green-800">{t('reports.ready')}</span>
            <a
              href={downloadUrl}
              download
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
            >
              {t('reports.download')}
            </a>
          </div>
        )}

        {status === 'error' && (
          <div className="rounded bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
            {error}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-center">{t('reports.note')}</p>
    </div>
  )
}
