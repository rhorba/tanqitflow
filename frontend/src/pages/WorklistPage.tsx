import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { worklistApi, type WorklistItem } from '../lib/api'

const STATUS_OPTIONS: WorklistItem['status'][] = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'DEFERRED']

const STATUS_BADGE: Record<WorklistItem['status'], string> = {
  OPEN: 'bg-blue-100 text-blue-700',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  RESOLVED: 'bg-green-100 text-green-700',
  DEFERRED: 'bg-gray-100 text-gray-600',
}

const ALERT_BADGE: Record<string, string> = {
  MNF: 'bg-purple-100 text-purple-700',
  ZSCORE: 'bg-indigo-100 text-indigo-700',
  ISOLATION_FOREST: 'bg-red-100 text-red-700',
  COMBINED: 'bg-orange-100 text-orange-700',
  NONE: 'bg-gray-100 text-gray-500',
}

function Toast({ message, type }: { message: string; type: 'success' | 'error' }) {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
        type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
      }`}
    >
      {message}
    </div>
  )
}

const PAGE_SIZE = 20

export default function WorklistPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterAlert, setFilterAlert] = useState<string>('')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['worklist', page, filterStatus],
    queryFn: () => worklistApi.list(page, PAGE_SIZE, filterStatus || undefined).then((r) => r.data),
    staleTime: 30_000,
  })

  const generateMutation = useMutation({
    mutationFn: () => worklistApi.generate(),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['worklist'] })
      showToast(t('worklist.generate_success', { count: res.data.generated }), 'success')
    },
    onError: () => showToast(t('common.error'), 'error'),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: WorklistItem['status'] }) =>
      worklistApi.updateStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['worklist'] }),
    onError: () => showToast(t('common.error'), 'error'),
  })

  const rows = (data?.data ?? []).filter(
    (r) => !filterAlert || r.alert_type === filterAlert
  )

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  const fmt = (n: number | null, dec = 0) =>
    n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: dec })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-xl font-bold text-gray-800">{t('worklist.title')}</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {generateMutation.isPending ? t('common.loading') : t('worklist.generate')}
          </button>
          <a
            href={worklistApi.exportCsvUrl()}
            download
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {t('common.export_csv')}
          </a>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(1) }}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-blue-400 outline-none"
        >
          <option value="">{t('worklist.all_statuses')}</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{t(`worklist.status_${s.toLowerCase()}`)}</option>
          ))}
        </select>
        <select
          value={filterAlert}
          onChange={(e) => { setFilterAlert(e.target.value); setPage(1) }}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-blue-400 outline-none"
        >
          <option value="">{t('worklist.all_alerts')}</option>
          {['MNF', 'ZSCORE', 'ISOLATION_FOREST', 'COMBINED'].map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      {isError && (
        <div className="rounded bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
          {t('common.error')}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.rank')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.dma')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.loss_m3')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.savings')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.confidence')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.alert_type')}</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('worklist.status')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      {Array.from({ length: 7 }).map((__, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-gray-200 rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : rows.length === 0
                ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-10 text-center text-gray-400 text-sm">
                        {t('worklist.no_items')}
                      </td>
                    </tr>
                  )
                : rows.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm font-bold text-gray-700">#{item.rank}</td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-mono font-semibold text-blue-700">{item.dma_code}</div>
                        {item.dma_name && (
                          <div className="text-xs text-gray-400">{item.dma_name}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums text-gray-700">
                        {fmt(item.estimated_loss_m3_per_month)} m³
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums font-medium text-gray-800">
                        {fmt(item.savings_mad_est)} MAD
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums">
                        <span className={`font-medium ${item.confidence_score >= 70 ? 'text-red-600' : item.confidence_score >= 40 ? 'text-orange-500' : 'text-gray-600'}`}>
                          {item.confidence_score}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ALERT_BADGE[item.alert_type] ?? ALERT_BADGE.NONE}`}>
                          {item.alert_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={item.status}
                          onChange={(e) =>
                            statusMutation.mutate({
                              id: item.id,
                              status: e.target.value as WorklistItem['status'],
                            })
                          }
                          className={`text-xs font-medium rounded-full px-2 py-0.5 border-0 outline-none cursor-pointer ${STATUS_BADGE[item.status]}`}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>
                              {t(`worklist.status_${s.toLowerCase()}`)}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-sm">
            <span className="text-gray-500">
              {t('dmas.page')} {page} / {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
              >
                ‹
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
              >
                ›
              </button>
            </div>
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}
