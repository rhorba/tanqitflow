import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dmaApi, leakApi, type DmaBalancePeriod } from '../lib/api'

// ---------------------------------------------------------------------------
// NRW % trend chart
// ---------------------------------------------------------------------------

function NrwTrendChart({ data }: { data: DmaBalancePeriod[] }) {
  const { t } = useTranslation()
  const sorted = [...data].sort((a, b) => a.period_start.localeCompare(b.period_start))
  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h2 className="text-base font-semibold text-gray-700 mb-4">{t('dma_detail.nrw_trend')}</h2>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={sorted} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="period_start"
            tick={{ fontSize: 10 }}
            tickFormatter={(v: string) => v.slice(0, 7)}
          />
          <YAxis tick={{ fontSize: 10 }} unit="%" width={36} domain={[0, 'auto']} />
          <Tooltip
            formatter={(val: number) => [`${val.toFixed(1)} %`, 'NRW %']}
            labelFormatter={(l: string) => l.slice(0, 7)}
          />
          <ReferenceLine y={25} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '25%', position: 'right', fontSize: 10 }} />
          <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="4 2" label={{ value: '40%', position: 'right', fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="nrw_pct"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// IWA balance breakdown table
// ---------------------------------------------------------------------------

function BalanceTable({ data }: { data: DmaBalancePeriod[] }) {
  const { t } = useTranslation()
  const sorted = [...data].sort((a, b) => b.period_start.localeCompare(a.period_start))
  const fmt = (n: number | null, dec = 0) =>
    n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: dec })
  const FLAG_CLS: Record<string, string> = {
    critical: 'text-red-600 font-semibold',
    warning: 'text-orange-500 font-medium',
    normal: 'text-green-600',
  }
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-700">{t('dma_detail.iwa_table')}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">{t('dma_detail.period')}</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">SIV m³</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">SCV m³</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">NRW m³</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">NRW %</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">ILI</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">{t('dma_detail.flag')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-sm">
                  {t('dma_detail.no_balance')}
                </td>
              </tr>
            ) : (
              sorted.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-mono text-gray-600">{row.period_start.slice(0, 7)}</td>
                  <td className="px-4 py-2 text-sm text-right tabular-nums text-gray-700">{fmt(row.siv_m3)}</td>
                  <td className="px-4 py-2 text-sm text-right tabular-nums text-gray-700">{fmt(row.scv_m3)}</td>
                  <td className="px-4 py-2 text-sm text-right tabular-nums text-gray-700">{fmt(row.nrw_m3)}</td>
                  <td className={`px-4 py-2 text-sm text-right tabular-nums ${FLAG_CLS[row.flag_level]}`}>
                    {fmt(row.nrw_pct, 1)} %
                  </td>
                  <td className="px-4 py-2 text-sm text-right tabular-nums text-gray-500">
                    {row.leakage_index != null ? fmt(row.leakage_index, 2) : '—'}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <span className={`capitalize ${FLAG_CLS[row.flag_level]}`}>{row.flag_level}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Anomaly events list
// ---------------------------------------------------------------------------

function AnomalyList({ dmaCode }: { dmaCode: string }) {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ['anomalies', dmaCode],
    queryFn: () => leakApi.getAnomalies(dmaCode, 1, 20).then((r) => r.data),
    enabled: !!dmaCode,
    staleTime: 60_000,
  })

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-700">{t('dma_detail.anomalies')}</h2>
      </div>
      {isLoading ? (
        <div className="p-4 animate-pulse space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 rounded" />
          ))}
        </div>
      ) : !data?.data?.length ? (
        <p className="px-5 py-6 text-sm text-gray-400">{t('dma_detail.no_anomalies')}</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {data.data.map((ev) => (
            <li key={ev.id} className="px-5 py-3 flex items-center justify-between gap-4 text-sm">
              <div>
                <span className="font-mono text-xs text-gray-400 mr-2">{ev.event_time.slice(0, 16).replace('T', ' ')}</span>
                <span className="font-medium text-gray-700">{ev.metric}</span>
              </div>
              <div className="flex items-center gap-3 tabular-nums">
                <span className="text-gray-600">{ev.value.toFixed(2)}</span>
                <span className={`font-semibold ${Math.abs(ev.zscore) >= 5 ? 'text-red-600' : 'text-orange-500'}`}>
                  z={ev.zscore.toFixed(2)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Latest leak indicator badge
// ---------------------------------------------------------------------------

function ConfidenceBadge({ dmaCode }: { dmaCode: string }) {
  const { t } = useTranslation()
  const { data } = useQuery({
    queryKey: ['leak-indicators', dmaCode, 1],
    queryFn: () => leakApi.getIndicators(dmaCode, 1, 1).then((r) => r.data),
    enabled: !!dmaCode,
    staleTime: 60_000,
  })
  const indicator = data?.data?.[0]
  if (!indicator) return null

  const score = indicator.confidence_score
  const color = score >= 70 ? 'bg-red-100 text-red-700' : score >= 40 ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-600'

  return (
    <div className="flex items-center gap-2">
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${color}`}>
        {t('dmas.confidence')}: {score}%
      </span>
      {indicator.alert_type !== 'NONE' && (
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-700">
          {indicator.alert_type}
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DmaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const { data: dma, isLoading: dmaLoading, isError } = useQuery({
    queryKey: ['dma', id],
    queryFn: () => dmaApi.getById(id!).then((r) => r.data),
    enabled: !!id,
    staleTime: 60_000,
  })

  const { data: balance, isLoading: balanceLoading } = useQuery({
    queryKey: ['dma-balance', id],
    queryFn: () => dmaApi.getBalanceHistory(id!, 12).then((r) => r.data),
    enabled: !!id,
    staleTime: 60_000,
  })

  if (isError) {
    return (
      <div className="rounded bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
        {t('common.error')}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/dmas')}
          className="mt-1 text-gray-400 hover:text-gray-700 text-lg leading-none"
          aria-label="back"
        >
          ←
        </button>
        <div className="flex-1">
          {dmaLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-6 w-48 bg-gray-200 rounded" />
              <div className="h-4 w-32 bg-gray-100 rounded" />
            </div>
          ) : dma ? (
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-bold text-gray-800">
                  <span className="font-mono text-blue-700">{dma.code}</span>
                  {' — '}
                  {dma.name}
                </h1>
                {dma.zone && (
                  <span className="text-sm text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                    {dma.zone}
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-4 text-sm text-gray-500 flex-wrap">
                {dma.pipe_length_km != null && (
                  <span>{t('dma_detail.pipe_km', { km: dma.pipe_length_km.toFixed(1) })}</span>
                )}
                {dma.connection_count != null && (
                  <span>{t('dma_detail.connections', { n: dma.connection_count })}</span>
                )}
                <ConfidenceBadge dmaCode={dma.code} />
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* NRW trend chart */}
      {balanceLoading ? (
        <div className="bg-white rounded-lg shadow p-5 animate-pulse h-60" />
      ) : (
        <NrwTrendChart data={balance?.data ?? []} />
      )}

      {/* IWA balance table */}
      {balanceLoading ? (
        <div className="bg-white rounded-lg shadow p-5 animate-pulse h-40" />
      ) : (
        <BalanceTable data={balance?.data ?? []} />
      )}

      {/* Anomaly events */}
      {dma && <AnomalyList dmaCode={dma.code} />}
    </div>
  )
}
