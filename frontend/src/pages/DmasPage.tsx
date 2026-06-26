import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { dmaApi, type DmaTableRow } from '../lib/api'

type SortKey = 'code' | 'name' | 'siv_m3' | 'nrw_m3' | 'nrw_pct' | 'confidence_score'
type SortDir = 'asc' | 'desc'

const FLAG_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-orange-100 text-orange-700',
  normal: 'bg-green-100 text-green-700',
}

function FlagBadge({ level }: { level: string }) {
  const { t } = useTranslation()
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${FLAG_BADGE[level] ?? FLAG_BADGE.normal}`}>
      {t(`map.${level}`)}
    </span>
  )
}

function SortHeader({
  label,
  colKey,
  current,
  dir,
  onSort,
}: {
  label: string
  colKey: SortKey
  current: SortKey
  dir: SortDir
  onSort: (k: SortKey) => void
}) {
  const active = current === colKey
  return (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-800"
      onClick={() => onSort(colKey)}
    >
      {label}
      <span className="ml-1 opacity-60">
        {active ? (dir === 'asc' ? '▲' : '▼') : '⇅'}
      </span>
    </th>
  )
}

const PAGE_SIZE = 50

export default function DmasPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<SortKey>('code')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['dmas', 'table', page],
    queryFn: () => dmaApi.getTable(page, PAGE_SIZE).then((r) => r.data),
    staleTime: 30_000,
  })

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = (data?.data ?? []).slice().sort((a: DmaTableRow, b: DmaTableRow) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    const cmp =
      typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number)
    return sortDir === 'asc' ? cmp : -cmp
  })

  const totalPages = data ? Math.ceil(data.meta.total / PAGE_SIZE) : 1

  const fmt = (n: number | null, dec = 0) =>
    n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: dec })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">{t('dmas.title')}</h1>

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
                <SortHeader label={t('dmas.code')} colKey="code" current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label={t('dmas.name')} colKey="name" current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('dmas.zone')}</th>
                <SortHeader label={t('dmas.siv')} colKey="siv_m3" current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label={t('dmas.nrw_m3')} colKey="nrw_m3" current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortHeader label={t('dmas.nrw_pct')} colKey="nrw_pct" current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{t('dmas.flag')}</th>
                <SortHeader label={t('dmas.confidence')} colKey="confidence_score" current={sortKey} dir={sortDir} onSort={handleSort} />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      {Array.from({ length: 8 }).map((__, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-gray-200 rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : sorted.length === 0
                ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-10 text-center text-gray-400 text-sm">
                        {t('dmas.no_data')}
                      </td>
                    </tr>
                  )
                : sorted.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-blue-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/dmas/${row.id}`)}
                    >
                      <td className="px-4 py-3 text-sm font-mono font-semibold text-blue-700">{row.code}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">{row.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{row.zone ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-700 text-right tabular-nums">{fmt(row.siv_m3)}</td>
                      <td className="px-4 py-3 text-sm text-gray-700 text-right tabular-nums">{fmt(row.nrw_m3)}</td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums">
                        <span className={
                          (row.nrw_pct ?? 0) >= 40 ? 'text-red-700 font-semibold'
                            : (row.nrw_pct ?? 0) >= 25 ? 'text-orange-600 font-semibold'
                            : 'text-gray-700'
                        }>
                          {fmt(row.nrw_pct, 1)} %
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <FlagBadge level={row.flag_level} />
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums">
                        {row.confidence_score > 0 ? (
                          <span className={`font-medium ${row.confidence_score >= 70 ? 'text-red-600' : row.confidence_score >= 40 ? 'text-orange-500' : 'text-gray-600'}`}>
                            {row.confidence_score}%
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>

        {/* Pagination */}
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
    </div>
  )
}
