export interface ViewerConfig { manifestUrl: string }
export interface Point3D { x: number; y: number; z: number }
export interface ViewerState { camera: Record<string, unknown> }
export type AnnotationType = 'POINT_MARK' | 'AREA_MARK'

export interface Annotation {
  id: string
  type: AnnotationType
  geometry: { position?: Point3D; center?: [number, number, number]; size?: [number, number, number]; rotation?: [number, number, number] }
  title: string
  description: string
  viewerState?: ViewerState
  createdAt: string
}

export interface Measurement {
  id: string
  startPoint: Point3D
  endPoint: Point3D
  createdAt: string
}
