import type { RecordDraft } from '@/types/student'
import type { Measurement, MeasurementPayload } from '@/types/viewer'

export function normalizeReport(value: unknown): RecordDraft {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const text = (key: string, legacy?: string) => typeof source[key] === 'string'
    ? source[key] as string : legacy && typeof source[legacy] === 'string' ? source[legacy] as string : ''
  return { overview: text('overview'), process: text('process'), evidenceDescription: text('evidenceDescription', 'evidence'), preliminaryConclusion: text('preliminaryConclusion', 'conclusion') }
}

export function measurementPayload(value: MeasurementPayload): MeasurementPayload {
  const point = (p: MeasurementPayload['startPoint']) => ({ x: p.x, y: p.y, z: p.z })
  return { startPoint: point(value.startPoint), endPoint: point(value.endPoint), title: value.title || '', description: value.description || '', viewerState: value.viewerState || {} }
}

export function measurementResults(value: Partial<Measurement> & MeasurementPayload) {
  const dx = value.endPoint?.x - value.startPoint?.x, dy = value.endPoint?.y - value.startPoint?.y, dz = value.endPoint?.z - value.startPoint?.z
  const number = (server: unknown, fallback: number) => typeof server === 'number' && Number.isFinite(server) ? server : fallback
  return {
    deltaX: number(value.deltaX, dx), deltaY: number(value.deltaY, dy), deltaZ: number(value.deltaZ, dz),
    horizontalDistance: number(value.horizontalDistance, Math.hypot(dx, dy)),
    verticalDistance: Math.abs(number(value.verticalDistance, Math.abs(dz))),
    distance: number(value.distance, Math.hypot(dx, dy, dz)),
  }
}

export function metric(value: number) {
  return Number.isFinite(value) ? (Math.abs(value) < 0.0005 ? 0 : value).toFixed(3) : '—'
}
