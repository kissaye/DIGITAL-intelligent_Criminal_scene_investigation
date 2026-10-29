import type { Bounds, CaseVersionStatus } from '@/types/case'

const statusMap: Record<CaseVersionStatus, { text: string; type: 'info' | 'warning' | 'success' | 'danger' }> = {
  DRAFT: { text: '草稿', type: 'info' },
  PROCESSING: { text: '处理中', type: 'warning' },
  READY: { text: '已就绪', type: 'success' },
  FAILED: { text: '失败', type: 'danger' },
}

export function statusMeta(status?: CaseVersionStatus) {
  return statusMap[status || 'DRAFT']
}

export function formatBytes(size?: number) {
  if (!size) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let index = 0
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1 }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

export function formatDate(value?: string) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-'
}

export function formatBounds(bounds: Bounds | null | undefined) {
  if (!bounds) return '-'
  const [minX, minY, minZ] = bounds.min
  const [maxX, maxY, maxZ] = bounds.max
  return `X: ${minX.toFixed(2)}–${maxX.toFixed(2)}；Y: ${minY.toFixed(2)}–${maxY.toFixed(2)}；Z: ${minZ.toFixed(2)}–${maxZ.toFixed(2)}`
}
