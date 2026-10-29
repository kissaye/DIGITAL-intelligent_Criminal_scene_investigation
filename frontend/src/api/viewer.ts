import http, { responseData } from '@/api/http'
import type { Annotation, Measurement, ViewerConfig } from '@/types/viewer'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const storeKey = (versionId: string, kind: string) => `dici.mock-viewer-${kind}-${versionId}`
const wait = (ms = 180) => new Promise((resolve) => window.setTimeout(resolve, ms))
const read = <T>(versionId: string, kind: string): T[] => JSON.parse(localStorage.getItem(storeKey(versionId, kind)) || '[]') as T[]
const write = <T>(versionId: string, kind: string, value: T[]) => localStorage.setItem(storeKey(versionId, kind), JSON.stringify(value))
const id = (prefix: string) => `${prefix}-${Date.now()}`

export async function getViewerConfig(versionId: string): Promise<ViewerConfig> {
  if (!useMock) return responseData<ViewerConfig>(await http.get(`/api/v1/case-versions/${versionId}/viewer-config`))
  await wait()
  // Mock 不伪造三维点云资源；iframe 只显示明确的模拟模式说明。
  return { manifestUrl: '' }
}

export async function getAnnotations(versionId: string): Promise<Annotation[]> {
  if (!useMock) return responseData<Annotation[]>(await http.get(`/api/v1/case-versions/${versionId}/annotations`))
  await wait(); return read<Annotation>(versionId, 'annotations')
}
export async function createAnnotation(versionId: string, payload: Omit<Annotation, 'id' | 'createdAt'>): Promise<Annotation> {
  if (!useMock) return responseData<Annotation>(await http.post(`/api/v1/case-versions/${versionId}/annotations`, payload))
  await wait(); const item: Annotation = { ...payload, id: id('annotation'), createdAt: new Date().toISOString() }; const list = read<Annotation>(versionId, 'annotations'); list.unshift(item); write(versionId, 'annotations', list); return item
}
export async function updateAnnotation(annotationId: string, payload: Omit<Annotation, 'id' | 'createdAt'>): Promise<Annotation> {
  if (!useMock) return responseData<Annotation>(await http.put(`/api/v1/annotations/${annotationId}`, payload))
  await wait(); const key = Object.keys(localStorage).find((value) => value.startsWith('dici.mock-viewer-annotations-') && read<Annotation>(value.replace('dici.mock-viewer-annotations-', ''), 'annotations').some((item) => item.id === annotationId)); if (!key) throw new Error('标记不存在'); const versionId = key.replace('dici.mock-viewer-annotations-', ''); const list = read<Annotation>(versionId, 'annotations'); const index = list.findIndex((item) => item.id === annotationId); const item = { ...payload, id: annotationId, createdAt: list[index].createdAt }; list[index] = item; write(versionId, 'annotations', list); return item
}
export async function deleteAnnotation(annotationId: string): Promise<void> {
  if (!useMock) { await http.delete(`/api/v1/annotations/${annotationId}`); return }
  await wait(); for (const key of Object.keys(localStorage).filter((value) => value.startsWith('dici.mock-viewer-annotations-'))) { const versionId = key.replace('dici.mock-viewer-annotations-', ''); const list = read<Annotation>(versionId, 'annotations'); if (list.some((item) => item.id === annotationId)) write(versionId, 'annotations', list.filter((item) => item.id !== annotationId)) }
}
export async function getMeasurements(versionId: string): Promise<Measurement[]> {
  if (!useMock) return responseData<Measurement[]>(await http.get(`/api/v1/case-versions/${versionId}/measurements`))
  await wait(); return read<Measurement>(versionId, 'measurements')
}
export async function createMeasurement(versionId: string, payload: Omit<Measurement, 'id' | 'createdAt'>): Promise<Measurement> {
  if (!useMock) return responseData<Measurement>(await http.post(`/api/v1/case-versions/${versionId}/measurements`, payload))
  await wait(); const item = { ...payload, id: id('measurement'), createdAt: new Date().toISOString() }; const list = read<Measurement>(versionId, 'measurements'); list.unshift(item); write(versionId, 'measurements', list); return item
}
export async function deleteMeasurement(measurementId: string): Promise<void> {
  if (!useMock) { await http.delete(`/api/v1/measurements/${measurementId}`); return }
  await wait(); for (const key of Object.keys(localStorage).filter((value) => value.startsWith('dici.mock-viewer-measurements-'))) { const versionId = key.replace('dici.mock-viewer-measurements-', ''); const list = read<Measurement>(versionId, 'measurements'); if (list.some((item) => item.id === measurementId)) write(versionId, 'measurements', list.filter((item) => item.id !== measurementId)) }
}
