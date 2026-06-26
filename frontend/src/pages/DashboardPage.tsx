import { useState } from 'react'
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
// Types
// ---------------------------------------------------------------------------

interface TrendPoint {
  month: string
  siv_m3: number
  nrw_m3: number
  nrw_pct: number
}

// ---------------------------------------------------------------------------
// KPI card with optional delta
// ---------------------------------------------------------------------------

interface KpiCardProps {
  label: string
  value: string | number
  unit?: string
  accent?: 'blue' | 'red' | 'orange' | 'yellow'
  delta?: number | null   // positive = worse (NRW up), negative = better
  deltaInvert?: boolean   // if true, positive delta = green (e.g. SIV going up is neutral)
}

function KpiCard({ label, value, unit, accent = 'blue', delta, deltaInvert }: KpiCardProps) {
  const accentClasses: Record<string, string> = {
    blue: 'border-t-4 border-blue-500',
    red: 'border-t-4 border-red-500',
    orange: 'border-t-4 border-orange-500',
    yellow: 'border-t-4 border-yellow-400',
  }

  const renderDelta = () => {
    if (delta === null || delta === undefined || delta === 0) return null
    const isPositive = delta > 0
    // For NRW metrics: positive (going up) = bad = red
    // deltaInvert=true means positive = good = green (e.g. for SIV)
    const isGood = deltaInvert ? isPositive : !isPositive
    return (
      <span className={`ml-2 text-sm font-medium ${isGood ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
      </span>
    )
  }

  return (
    <div className={`bg-white rounded-lg shadow p-5 ${accentClasses[accent]}`}>
      <p className="text-sm text-gray-500 truncate">{label}</p>
      <div className="mt-1 flex items-baseline">
        <p className="text-3xl font-bold text-gray-900">
          {value}
          {unit && <span className="ml-1 text-lg font-normal text-gray-500">{unit}</span>}
        </p>
        {renderDelta()}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Date range selector
// ---------------------------------------------------------------------------

const RANGE_OPTIONS = [
  { months: 1, key: 'common.last_1m' },
  { months: 3, key: 'common.last_3m' },
  { months: 6, key: 'common.last_6m' },
  { months: 12, key: 'common.last_12m' },
]

function RangeSelector({
  value,
  onChange,
}: {
  value: number
  onChange: (m: number) => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
      {RANGE_OPTIONS.map(({ months, key }) => (
        <button
          key={months}
          onClick={() => onChange(months)}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            value === months
              ? 'bg-white text-blue-700 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {t(key)}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Trend chart
// ---------------------------------------------------------------------------

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
  const [months, setMonths] = useState(12)

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: ['balance', 'summary'],
    queryFn: () => balanceApi.getSummary().then((r) => r.data),
    staleTime: 60_000,
    retry: 1,
  })

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['balance', 'trend', months],
    queryFn: () => balanceApi.getTrend(months).then((r) => r.data),
    staleTime: 60_000,
    retry: 1,
  })

  // Compute delta from the last two trend points (sorted ascending)
  const computeDelta = (key: keyof TrendPoint): number | null => {
    if (!trend || trend.length < 2) return null
    const sorted = [...trend].sort((a, b) => a.month.localeCompare(b.month))
    const prev = sorted[sorted.length - 2][key] as number
    const curr = sorted[sorted.length - 1][key] as number
    if (prev === 0) return null
    return ((curr - prev) / prev) * 100
  }

  const fmt = (n: number, decimals = 0) =>
    n.toLocaleString(undefined, { maximumFractionDigits: decimals })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">{t('dashboard.title')}</h1>
        <RangeSelector value={months} onChange={setMonths} />
      </div>

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
              delta={computeDelta('siv_m3')}
              deltaInvert
            />
            <KpiCard
              label={t('dashboard.nrw_m3')}
              value={summary ? fmt(summary.nrw_m3) : '—'}
              unit="m³"
              accent="orange"
              delta={computeDelta('nrw_m3')}
            />
            <KpiCard
              label={t('dashboard.nrw_pct')}
              value={summary ? fmt(summary.nrw_pct, 1) : '—'}
              unit="%"
              accent={
                !summary ? 'blue'
                  : summary.nrw_pct >= 40 ? 'red'
                  : summary.nrw_pct >= 25 ? 'orange'
                  : 'blue'
              }
              delta={computeDelta('nrw_pct')}
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
