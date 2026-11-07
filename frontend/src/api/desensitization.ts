import http, { responseData } from '@/api/http'
import type { BoxRange, DerivedVersionResult, DesensitizationRule, DesensitizationRulePayload, DesensitizationRuleStatus, DesensitizationRuleType } from '@/types/desensitization'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const wait = (ms = 180) => new Promise((resolve) => window.setTimeout(resolve, ms))
const key = (versionId: string) => `dici.mock-desensitization-rules-${versionId}`
const derivedKey = (versionId: string) => `dici.mock-desensitization-derived-${versionId}`
const unknownRange: BoxRange = { min: [0, 0, 0], max: [1, 1, 1] }

type LooseRecord = Record<string, unknown>
const record = (value: unknown): LooseRecord => value && typeof value === 'object' ? value as LooseRecord : {}
const asText = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const asNumber = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null
const triple = (value: unknown, fallback: [number, number, number]): [number, number, number] => Array.isArray(value) && value.length >= 3 && value.slice(0, 3).every((item) => typeof item === 'number') ? [value[0] as number, value[1] as number, value[2] as number] : fallback
const rangeOf = (value: unknown): BoxRange => {
  const source = record(value)
  return { min: triple(source.min ?? source.minimum, unknownRange.min), max: triple(source.max ?? source.maximum, unknownRange.max) }
}

export function mapDesensitizationRule(value: unknown): DesensitizationRule {
  const source = record(value); const type = source.mode === 'DELETE' ? 'DELETE' : 'HIDE'
  const rawStatus = asText(source.status, 'DRAFT')
  const status: DesensitizationRuleStatus = ['DRAFT', 'APPLIED', 'PROCESSING', 'READY', 'FAILED'].includes(rawStatus) ? rawStatus as DesensitizationRuleStatus : 'UNKNOWN'
  return { id: asText(source.id, `unknown-${Date.now()}`), type, title: asText(source.title, type === 'HIDE' ? '遮挡区域' : '删除区域'), description: asText(source.description), range: rangeOf(source.geometry), status, enforced: source.enforced === true, createdAt: typeof source.createdAt === 'string' ? source.createdAt : null }
}
const toRequest = (payload: DesensitizationRulePayload) => ({ mode: payload.type, geometry: { type: 'BOX', min: payload.range.min, max: payload.range.max }, title: payload.title, description: payload.description })

function readMock(versionId: string): DesensitizationRule[] {
  try {
    const values = JSON.parse(localStorage.getItem(key(versionId)) || '[]') as unknown[]
    return values.map(value => {
      const rule = record(value)
      return mapDesensitizationRule({ ...rule, mode: rule.mode ?? rule.type, geometry: rule.geometry ?? rule.range })
    })
  } catch { return [] }
}
function writeMock(versionId: string, rules: DesensitizationRule[]) { localStorage.setItem(key(versionId), JSON.stringify(rules)) }
function mapResult(value: unknown): DerivedVersionResult {
  const source = record(value)
  const statusValue = asText(source.status, 'UNKNOWN')
  const status = ['DRAFT', 'PROCESSING', 'READY', 'PUBLISHED', 'ARCHIVED', 'FAILED'].includes(statusValue) ? statusValue as DerivedVersionResult['status'] : 'UNKNOWN'
  return { versionId: asText(source.versionId) || null, parentVersionId: asText(source.parentVersionId) || null, status, jobId: asText(source.jobId) || null, progress: asNumber(source.progress), failureReason: asText(source.failureReason) || null }
}

export async function getDesensitizationRules(versionId: string): Promise<DesensitizationRule[]> {
  if (useMock) { await wait(); return readMock(versionId) }
  const body = responseData<unknown>(await http.get(`/api/v1/case-versions/${versionId}/desensitization-rules`))
  const source = record(body); const items = Array.isArray(body) ? body : Array.isArray(source.items) ? source.items : Array.isArray(source.rules) ? source.rules : []
  return items.map(mapDesensitizationRule)
}
export async function createDesensitizationRule(versionId: string, payload: DesensitizationRulePayload): Promise<DesensitizationRule> {
  if (!useMock) return mapDesensitizationRule(responseData<unknown>(await http.post(`/api/v1/case-versions/${versionId}/desensitization-rules`, toRequest(payload))))
  await wait(); const item: DesensitizationRule = { ...payload, id: `mock-rule-${Date.now()}`, status: 'DRAFT', enforced: false, createdAt: new Date().toISOString() }; const items = readMock(versionId); items.unshift(item); writeMock(versionId, items); return item
}
export async function updateDesensitizationRule(ruleId: string, payload: DesensitizationRulePayload): Promise<DesensitizationRule> {
  if (!useMock) return mapDesensitizationRule(responseData<unknown>(await http.put(`/api/v1/desensitization-rules/${ruleId}`, toRequest(payload))))
  await wait(); for (const storageKey of Object.keys(localStorage).filter((item) => item.startsWith('dici.mock-desensitization-rules-'))) { const versionId = storageKey.replace('dici.mock-desensitization-rules-', ''); const items = readMock(versionId); const index = items.findIndex((item) => item.id === ruleId); if (index >= 0) { items[index] = { ...items[index], ...payload }; writeMock(versionId, items); return items[index] } } throw new Error('脱敏规则不存在')
}
export async function deleteDesensitizationRule(ruleId: string): Promise<void> {
  if (!useMock) { await http.delete(`/api/v1/desensitization-rules/${ruleId}`); return }
  await wait(); for (const storageKey of Object.keys(localStorage).filter((item) => item.startsWith('dici.mock-desensitization-rules-'))) { const versionId = storageKey.replace('dici.mock-desensitization-rules-', ''); const items = readMock(versionId); if (items.some((item) => item.id === ruleId)) writeMock(versionId, items.filter((item) => item.id !== ruleId)) }
}
export async function applyDesensitization(versionId: string): Promise<DerivedVersionResult> {
  if (!useMock) return mapResult(responseData<unknown>(await http.post(`/api/v1/case-versions/${versionId}/desensitization/apply`)))
  await wait(320); const current = readMock(versionId); if (!current.length) throw new Error('请先创建至少一条脱敏规则')
  const result: DerivedVersionResult = { versionId: `mock-derived-${Date.now()}`, parentVersionId: versionId, status: 'PROCESSING', jobId: null, progress: null, failureReason: null }
  localStorage.setItem(derivedKey(versionId), JSON.stringify(result)); return result
}
