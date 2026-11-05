import type { CaseVersionStatus } from '@/types/case'

export interface AuthorizationRecord { id: string; reference: string; scope: string; validUntil: string | null; revokedAt: string | null }
export interface PublicationInfo { authorizationId: string; validUntil: string; publishedAt: string; checksum: string; reviewNote: string }
export interface VersionLineage { id: string; versionNumber: number; parentVersionId: string | null; status: CaseVersionStatus; publication: PublicationInfo | null; createdAt: string }
export interface AuditLog { id: string; action: string; actorId: string | number; createdAt: string; detail: unknown }
export interface AuditPage { items: AuditLog[]; total: number }
