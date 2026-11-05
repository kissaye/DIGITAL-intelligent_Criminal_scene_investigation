import http, { responseData } from '@/api/http'
import type { AuditPage, AuthorizationRecord, VersionLineage } from '@/types/publication'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const unavailable = () => Promise.reject(new Error('发布管理需要真实后端，请设置 VITE_USE_MOCK=false。'))
export async function getAuthorizations(caseId: string) { if (useMock) return [] as AuthorizationRecord[]; return responseData<AuthorizationRecord[]>(await http.get(`/api/v1/cases/${caseId}/authorizations`)) }
export async function createAuthorization(caseId: string, payload: Omit<AuthorizationRecord, 'id' | 'revokedAt'>) { if (useMock) return unavailable(); return responseData<AuthorizationRecord>(await http.post(`/api/v1/cases/${caseId}/authorizations`, payload)) }
export async function revokeAuthorization(authorizationId: string) { if (useMock) return unavailable(); await http.post(`/api/v1/authorizations/${authorizationId}/revoke`) }
export async function getVersionLineage(caseId: string) { if (useMock) return [] as VersionLineage[]; return responseData<VersionLineage[]>(await http.get(`/api/v1/cases/${caseId}/versions`)) }
export async function publishVersion(versionId: string, payload: { authorizationId: string; validUntil: string | null; reviewNote: string; reviewConfirmed: boolean }) { if (useMock) return unavailable(); return responseData<VersionLineage>(await http.post(`/api/v1/case-versions/${versionId}/publish`, payload, { timeout: 600000 })) }
export async function archiveVersion(versionId: string) { if (useMock) return unavailable(); return responseData<VersionLineage>(await http.post(`/api/v1/case-versions/${versionId}/archive`)) }
export async function getAuditLogs(caseId: string, action: string, offset: number, limit = 20) { if (useMock) return { items: [], total: 0 } as AuditPage; return responseData<AuditPage>(await http.get('/api/v1/audit-logs', { params: { caseId, action: action || undefined, offset, limit } })) }
