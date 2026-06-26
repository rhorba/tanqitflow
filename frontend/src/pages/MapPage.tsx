import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import type { StyleFunction, Layer } from 'leaflet'
import type { Feature, GeoJsonObject } from 'geojson'
import 'leaflet/dist/leaflet.css'
import '../lib/leaflet-setup'
import HeatmapLayer from '../components/map/HeatmapLayer'
import { mapApi, type DmaFeatureProperties } from '../lib/api'

// Morocco center
const MOROCCO_CENTER: [number, number] = [31.7917, -7.0926]
const INITIAL_ZOOM = 6

const FLAG_COLORS: Record<string, string> = {
  normal: '#22c55e',
  warning: '#f59e0b',
  critical: '#ef4444',
}

function flagColor(flag: string | undefined): string {
  return FLAG_COLORS[flag ?? 'normal'] ?? FLAG_COLORS.normal
}

const polygonStyle: StyleFunction = (feature) => ({
  fillColor: flagColor(feature?.properties?.flag_level),
  fillOpacity: 0.45,
  color: '#ffffff',
  weight: 1.5,
  opacity: 0.8,
})

function onEachFeature(feature: Feature, layer: Layer) {
  const p = feature.properties as DmaFeatureProperties
  if (!p) return

  const nrwPct = p.nrw_pct != null ? p.nrw_pct.toFixed(1) + ' %' : '—'
  const nrwM3 = p.nrw_m3 != null ? p.nrw_m3.toLocaleString() + ' m³' : '—'

  layer.bindPopup(`
    <div class="text-sm min-w-[160px]">
      <p class="font-semibold text-gray-900 mb-1">${p.name}</p>
      <p class="text-gray-500 text-xs mb-2">${p.code}${p.zone ? ' · ' + p.zone : ''}</p>
      <div class="space-y-0.5">
        <div class="flex justify-between gap-4">
          <span class="text-gray-500">NRW %</span>
          <span class="font-medium">${nrwPct}</span>
        </div>
        <div class="flex justify-between gap-4">
          <span class="text-gray-500">NRW m³</span>
          <span class="font-medium">${nrwM3}</span>
        </div>
      </div>
    </div>
  `)
}

function MapLegend({ t }: { t: (k: string) => string }) {
  const items = [
    { key: 'normal', label: t('map.normal') },
    { key: 'warning', label: t('map.warning') },
    { key: 'critical', label: t('map.critical') },
  ]

  return (
    <div className="absolute bottom-8 right-4 z-[1000] bg-white rounded-lg shadow-md px-4 py-3 text-sm">
      <p className="font-semibold text-gray-700 mb-2">{t('map.legend')}</p>
      <div className="space-y-1.5">
        {items.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: FLAG_COLORS[key] }}
            />
            <span className="text-gray-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function MapPage() {
  const { t } = useTranslation()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dmas-geojson'],
    queryFn: () => mapApi.getGeoJSON().then((r) => r.data),
    staleTime: 300_000,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('map.title')}</h1>

      {isLoading && (
        <div className="flex items-center justify-center h-96 text-gray-500">
          {t('common.loading')}
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center justify-center h-96 gap-3 text-red-600">
          <p>{t('common.error')}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-red-100 rounded-lg text-sm hover:bg-red-200 transition-colors"
          >
            {t('common.retry')}
          </button>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="relative rounded-xl overflow-hidden shadow-md border border-gray-200">
          <MapContainer
            center={MOROCCO_CENTER}
            zoom={INITIAL_ZOOM}
            style={{ height: '620px', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              maxZoom={19}
            />

            {data && data.features.length > 0 && (
              <>
                <GeoJSON
                  key={data.features.length}
                  data={data as unknown as GeoJsonObject}
                  style={polygonStyle}
                  onEachFeature={onEachFeature}
                />
                <HeatmapLayer points={data.heat_points} />
              </>
            )}
          </MapContainer>

          {data && <MapLegend t={t} />}
        </div>
      )}

      {data && data.features.length === 0 && (
        <p className="text-center text-gray-500 mt-6">{t('map.no_data')}</p>
      )}
    </div>
  )
}
