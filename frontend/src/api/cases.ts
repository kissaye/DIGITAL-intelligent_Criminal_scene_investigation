import http, { responseData } from '@/api/http'
import type { CaseFile, CaseListResult, CaseRecord, CaseVersion, CreateCasePayload } from '@/types/case'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const MOCK_KEY = 'dici.mock-cases'

const wait = (milliseconds = 300) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

function readMockCases(): CaseRecord[] {
  const raw = localStorage.getItem(MOCK_KEY)
  if (raw) {
    const records = JSON.parse(raw) as CaseRecord[]
    const normalized = records.map((record) => {
      if (!record.latestVersion) return { ...record, validUntil: record.validUntil || null, file: record.file || null, latestVersion: null }
      const version = record.latestVersion as CaseVersion & { bounds?: unknown }
      return {
        ...record,
        validUntil: record.validUntil || null,
        file: record.file || null,
        latestVersion: {
          ...version,
          jobId: version.jobId || null,
          progress: version.progress ?? null,
          pointCount: version.pointCount ?? null,
          bounds: typeof version.bounds === 'object' && version.bounds !== null ? version.bounds as CaseVersion['bounds'] : null,
          failureReason: version.failureReason || null,
        },
      }
    })
    writeMockCases(normalized)
    return normalized
  }
  const seed: CaseRecord[] = [{
    id: 'mock-case-001', internalCode: 'DEMO-2026-001', teachingTitle: '教学演示案例', caseType: '其他', difficulty: '基础', courseTags: ['现场勘查'], desensitizationLevel: '二级',
    file: { id: 'mock-file-001', fileName: 'demo-scene.laz', fileSize: 18_874_368 },
    validUntil: null,
    latestVersion: { id: 'mock-version-001', status: 'READY', jobId: null, progress: 100, pointCount: 1_280_000, bounds: { min: [0, 0, 0], max: [24.61, 18.42, 3.25] }, failureReason: null, createdAt: new Date().toISOString() },
    createdAt: new Date().toISOString(),
  }]
  writeMockCases(seed)
  return seed
}

function writeMockCases(cases: CaseRecord[]) { localStorage.setItem(MOCK_KEY, JSON.stringify(cases)) }
function newId(prefix: string) { return `${prefix}-${Date.now()}` }
function findMockCase(caseId: string) {
  const item = readMockCases().find((record) => record.id === caseId)
  if (!item) throw new Error('案例不存在或已被删除')
  return item
}

export async function createCase(payload: CreateCasePayload): Promise<CaseRecord> {
  if (!useMock) return responseData<CaseRecord>(await http.post('/api/v1/cases', payload))
  await wait()
  const record: CaseRecord = { id: newId('mock-case'), ...payload, validUntil: payload.validUntil || null, file: null, latestVersion: null, createdAt: new Date().toISOString() }
  const cases = readMockCases(); cases.unshift(record); writeMockCases(cases)
  return record
}

export async function getCases(): Promise<CaseListResult> {
  if (!useMock) return responseData<CaseListResult>(await http.get('/api/v1/cases'))
  await wait(180)
  const items = readMockCases()
  return { items, total: items.length }
}

export async function getCase(caseId: string): Promise<CaseRecord> {
  if (!useMock) return responseData<CaseRecord>(await http.get(`/api/v1/cases/${caseId}`))
  await wait(180)
  return findMockCase(caseId)
}

/** 上传接口的 data 为新建文件记录，调用方必须保存其 id 以创建转换版本。 */
export async function uploadCaseFile(caseId: string, file: File): Promise<CaseFile> {
  if (!useMock) {
    const formData = new FormData(); formData.append('upload', file)
    return responseData<CaseFile>(await http.post(`/api/v1/cases/${caseId}/files`, formData))
  }
  await wait(500)
  const cases = readMockCases(); const record = findMockCase(caseId)
  const uploadedFile: CaseFile = { id: newId('mock-file'), fileName: file.name, fileSize: file.size }
  record.file = uploadedFile
  const index = cases.findIndex((item) => item.id === caseId); cases[index] = record; writeMockCases(cases)
  return uploadedFile
}

export async function createCaseVersion(caseId: string, fileId: string): Promise<CaseVersion> {
  if (!useMock) return responseData<CaseVersion>(await http.post(`/api/v1/cases/${caseId}/versions`, { fileId }))
  await wait(350)
  const cases = readMockCases(); const record = findMockCase(caseId)
  if (!record.file || record.file.id !== fileId) throw new Error('上传文件记录无效，请重新上传')
  const version: CaseVersion = { id: newId('mock-version'), jobId: newId('mock-job'), status: 'PROCESSING', progress: 15, pointCount: null, bounds: null, failureReason: null, createdAt: new Date().toISOString() }
  record.latestVersion = version
  cases[cases.findIndex((item) => item.id === caseId)] = record; writeMockCases(cases)
  return version
}

export async function getCaseVersion(versionId: string): Promise<CaseVersion> {
  if (!useMock) return responseData<CaseVersion>(await http.get(`/api/v1/case-versions/${versionId}`))
  await wait(180)
  const version = readMockCases().flatMap((record) => record.latestVersion ? [record.latestVersion] : []).find((item) => item.id === versionId)
  if (!version) throw new Error('转换版本不存在')
  return version
}

export async function getJob(jobId: string): Promise<{ id: string; status: CaseVersion['status']; progress: number | null; failureReason: string | null }> {
  if (!useMock) return responseData<CaseVersion>(await http.get(`/api/v1/jobs/${jobId}`))
  await wait(220)
  const cases = readMockCases(); const record = cases.find((item) => item.latestVersion?.jobId === jobId)
  if (!record?.latestVersion) throw new Error('转换任务不存在')
  const version = record.latestVersion
  if (version.status === 'PROCESSING') {
    version.progress = Math.min((version.progress || 0) + 35, 100)
    if (version.progress >= 100) Object.assign(version, { status: 'READY', jobId: null, pointCount: 1_024_000, bounds: { min: [0, 0, 0], max: [20.35, 15.8, 3.1] } })
    writeMockCases(cases)
  }
  return { id: jobId, status: version.status, progress: version.progress, failureReason: version.failureReason }
}
