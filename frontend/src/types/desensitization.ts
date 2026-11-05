import type { CaseVersionStatus } from '@/types/case'

export type DesensitizationRuleType = 'HIDE' | 'DELETE'
export type DesensitizationRuleStatus = 'DRAFT' | 'APPLIED' | 'PROCESSING' | 'READY' | 'FAILED' | 'UNKNOWN'

export interface BoxRange {
  min: [number, number, number]
  max: [number, number, number]
}

export interface DesensitizationRule {
  id: string
  type: DesensitizationRuleType
  title: string
  description: string
  range: BoxRange
  status: DesensitizationRuleStatus
  /** Viewer 配置下发的强制 HIDE 规则不可由当前页面移除。 */
  enforced: boolean
  createdAt: string | null
}

export interface DesensitizationRulePayload {
  type: DesensitizationRuleType
  title: string
  description: string
  range: BoxRange
}

export interface DerivedVersionResult {
  versionId: string | null
  parentVersionId: string | null
  status: CaseVersionStatus | 'UNKNOWN'
  jobId: string | null
  progress: number | null
  failureReason: string | null
}

export interface DesensitizationRuleResponse {
  id: string
  mode: DesensitizationRuleType
  geometry: { type: 'BOX'; min: [number, number, number]; max: [number, number, number] }
  title: string
  description: string
  status: string
  createdAt?: string | null
}

export interface ViewerMask {
  id: string
  type: 'HIDE' | 'DELETE'
  title: string
  description: string
  range: BoxRange
  enforced: boolean
}
