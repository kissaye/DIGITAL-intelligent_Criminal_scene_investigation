export type CaseVersionStatus = 'DRAFT' | 'PROCESSING' | 'READY' | 'FAILED'

export interface CaseFile {
  id: string
  fileName: string
  fileSize: number
}

export interface Bounds {
  min: [number, number, number]
  max: [number, number, number]
}

export interface CaseVersion {
  id: string
  status: CaseVersionStatus
  jobId: string | null
  progress: number | null
  pointCount: number | null
  bounds: Bounds | null
  failureReason: string | null
  createdAt: string
}

export interface CaseRecord {
  id: string
  internalCode: string
  teachingTitle: string
  caseType: string
  difficulty: string
  courseTags: string[]
  validUntil: string | null
  desensitizationLevel: string
  file: CaseFile | null
  latestVersion: CaseVersion | null
  createdAt: string
}

export interface CreateCasePayload {
  internalCode: string
  teachingTitle: string
  caseType: string
  difficulty: string
  courseTags: string[]
  validUntil?: string | null
  desensitizationLevel: string
}

export interface CaseListResult {
  items: CaseRecord[]
  total: number
}
