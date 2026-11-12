import type { Point3D, ViewerState } from './viewer'
export interface AreaPayload {
  points: Point3D[]
  title?: string | null
  description?: string | null
  viewerState?: ViewerState
}
export interface AreaMeasurement extends AreaPayload {
  id: string
  pointCount?: number
  area?: number
  perimeter?: number
  maxPlaneDeviation?: number
  caseVersionId?: string
  createdAt?: string
  updatedAt?: string
}
export function areaPayload(value: AreaPayload): AreaPayload {
  return { points: value.points.map(({x,y,z}) => ({x,y,z})), title:value.title || '', description:value.description || '', viewerState:value.viewerState || {} }
}
