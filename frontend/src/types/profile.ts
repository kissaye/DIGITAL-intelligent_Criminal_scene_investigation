import type { Point3D, ViewerState } from './viewer'
export interface ProfilePayload { points: Point3D[]; width: number; title?: string | null; description?: string | null; viewerState?: ViewerState }
export interface ProfileRecord extends ProfilePayload { id: string; pointCount?: number; pathLength?: number; caseVersionId?: string; createdAt?: string; updatedAt?: string }
export function profilePayload(value: ProfilePayload): ProfilePayload {
  return { points: value.points.map(({x,y,z}) => ({x,y,z})), width: value.width, title:value.title || '', description:value.description || '', viewerState:value.viewerState || {} }
}
