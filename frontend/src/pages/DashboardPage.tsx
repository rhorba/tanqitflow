import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { balanceApi } from '../lib/api'

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------

interface KpiCardProps {
  label: string
  value: string | number
  unit?: string
  accent?: 'blue' | 'red' | 'orange' | 'yellow'
}

function KpiCard({ label, value, unit, accent = 'blue' }: KpiCardProps) {
  const accentClasses: Record<string, string> = {
    blue: 'border-t-4 border-blue-500',
    red: 'border-t-4 border-red-500',
    orange: 'border-t-4 border-orange-500',
    yellow: 'border-t-4 border-yellow-400',
  }
  return (
    <div className={`bg-white rounded-lg shadow p-5 ${accentClasses[accent]}`}>
      <p className="text-sm text-gray-500 truncate">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">
        {value}
        {unit && <span className="ml-1 text-lg font-normal text-gray-500">{unit}</span>}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Trend chart
// ---------------------------------------------------------------------------

interface TrendPoint {
  month: string
  siv_m3: number
  nrw_m3: number
  nrw_pct: number
}

function TrendChart({ data, title }: { data: TrendPoint[]; title: string }) {
  const sorted = [...data].sort((a, b) => a.month.localeCompare(b.month))

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h2 className="text-base font-semibold text-gray-700 mb-4">{title}</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={sorted} margin={{ top: 4, right: 20, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis yAxisId="pct" domain={[0, 'auto']} tick={{ fontSize: 11 }} unit="%" width={40} />
          <YAxis yAxisId="vol" orientation="right" tick={{ fontSize: 11 }} unit="m³" width={60} />
          <Tooltip
            formatter={(val: number, name: string) => [
              name === 'nrw_pct' ? `${val.toFixed(1)} %` : `${val.toLocaleString()} m³`,
              name,
            ]}
          />
          <Legend />
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="nrw_pct"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            yAxisId="vol"
            type="monotone"
            dataKey="nrw_m3"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3 }}
            strokeDasharray="4 2"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { t } = useTranslation()

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: ['balance', 'summary'],
    queryFn: () => balanceApi.getSummary().then((r) => r.data),
    staleTime: 5 * 60_000,
    retry: 1,
  })

  const {
    data: trend,
    isLoading: trendLoading,
  } = useQuery({
    queryKey: ['balance', 'trend', 12],
    queryFn: () => balanceApi.getTrend(12).then((r) => r.data),
    staleTime: 5 * 60_000,
    retry: 1,
  })

  const fmt = (n: number, decimals = 0) =>
    n.toLocaleString(undefined, { maximumFractionDigits: decimals })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">{t('dashboard.title')}</h1>

      {summaryError && (
        <div className="rounded bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
          {t('common.error')}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg shadow p-5 animate-pulse h-24" />
          ))
        ) : (
          <>
            <KpiCard
              label={t('dashboard.siv')}
              value={summary ? fmt(summary.siv_m3) : '—'}
              unit="m³"
              accent="blue"
            />
            <KpiCard
              label={t('dashboard.nrw_m3')}
              value={summary ? fmt(summary.nrw_m3) : '—'}
              unit="m³"
              accent="orange"
            />
            <KpiCard
              label={t('dashboard.nrw_pct')}
              value={summary ? fmt(summary.nrw_pct, 1) : '—'}
              unit="%"
              accent={
                !summary
                  ? 'blue'
                  : summary.nrw_pct >= 40
                    ? 'red'
                    : summary.nrw_pct >= 25
                      ? 'orange'
                      : 'blue'
              }
            />
            <KpiCard
              label={t('dashboard.flagged_dmas')}
              value={summary ? fmt(summary.flagged_dmas) : '—'}
              accent={summary && summary.flagged_dmas > 0 ? 'yellow' : 'blue'}
            />
          </>
        )}
      </div>

      {/* Trend chart */}
      {trendLoading ? (
        <div className="bg-white rounded-lg shadow p-5 animate-pulse h-72" />
      ) : trend && trend.length > 0 ? (
        <TrendChart data={trend} title={t('dashboard.trend')} />
      ) : (
        !trendLoading && (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400 text-sm">
            {t('common.loading')}
          </div>
        )
      )}
    </div>
  )
}
