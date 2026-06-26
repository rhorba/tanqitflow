import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

interface Props {
  points: [number, number, number][] // [lat, lng, intensity 0–1]
}

export default function HeatmapLayer({ points }: Props) {
  const map = useMap()

  useEffect(() => {
    if (!points.length) return

    const heat = L.heatLayer(points, {
      radius: 40,
      blur: 30,
      maxZoom: 17,
      max: 1.0,
      gradient: { 0.3: '#22c55e', 0.6: '#f59e0b', 1.0: '#ef4444' },
    })
    heat.addTo(map)

    return () => {
      heat.remove()
    }
  }, [map, points])

  return null
}
