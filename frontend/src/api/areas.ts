import http, { responseData } from './http'
import { areaPayload, type AreaMeasurement, type AreaPayload } from '@/types/area'
const mock = import.meta.env.VITE_USE_MOCK !== 'false'
const key = (id: string) => 'dici.mock-areas-' + id
export async function getAreas(versionId: string): Promise<AreaMeasurement[]> {
  return mock ? JSON.parse(localStorage.getItem(key(versionId)) || '[]') : responseData(await http.get('/api/v1/case-versions/'+versionId+'/area-measurements'))
}
export async function createArea(versionId: string, value: AreaPayload): Promise<AreaMeasurement> {
  if (!mock) return responseData(await http.post('/api/v1/case-versions/'+versionId+'/area-measurements', areaPayload(value)))
  const item = { ...areaPayload(value), id:crypto.randomUUID() }
  localStorage.setItem(key(versionId), JSON.stringify([item,...await getAreas(versionId)]))
  return item
}
export async function deleteArea(versionId: string, id: string) {
  if (!mock) { await http.delete('/api/v1/area-measurements/'+id); return }
  localStorage.setItem(key(versionId),JSON.stringify((await getAreas(versionId)).filter(item=>item.id!==id)))
}
export function areaError(error: unknown) {
  const data = (error as {response?:{data?:{message?:unknown;details?:unknown;detail?:unknown}}})?.response?.data
  const detail = data?.details ?? data?.detail
  return typeof data?.message==='string' ? data.message : typeof detail==='string' ? detail : Array.isArray(detail) ? detail.map(item=>typeof item==='string'?item:item.msg || '').filter(Boolean).join('；') || '区域数据无效，请检查选点' : error instanceof Error ? error.message : '区域保存失败，请重试'
}
