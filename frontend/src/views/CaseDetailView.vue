<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { getCase, getCaseVersion, getJob } from '@/api/cases'
import type { CaseRecord } from '@/types/case'
import { formatBounds, formatBytes, formatDate, statusMeta } from '@/utils/case'

const route = useRoute(); const router = useRouter()
const record = ref<CaseRecord>(); const loading = ref(false); const timer = ref<number>()
const version = computed(() => record.value?.latestVersion)

async function loadDetail(silent = false) {
  if (!silent) loading.value = true
  try {
    const current = await getCase(String(route.params.caseId))
    if (current.latestVersion?.jobId && current.latestVersion.status === 'PROCESSING') await getJob(current.latestVersion.jobId)
    if (current.latestVersion) current.latestVersion = await getCaseVersion(current.latestVersion.id)
    record.value = current
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '案例详情加载失败') }
  finally { loading.value = false }
}

function refresh() { loadDetail().then(() => ElMessage.success('状态已更新')) }
onMounted(async () => { await loadDetail(); timer.value = window.setInterval(() => { if (version.value?.status === 'PROCESSING') loadDetail(true) }, 5000) })
onBeforeUnmount(() => { if (timer.value) window.clearInterval(timer.value) })
</script>

<template>
  <main class="page-shell">
    <div class="page-header"><div><p class="eyebrow">管理员 / 案例管理</p><h1>{{ record?.teachingTitle || '案例详情' }}</h1><p class="page-description">案例与转换版本信息</p></div><div class="header-actions"><el-button @click="router.push('/admin/cases')">返回列表</el-button><el-button type="primary" :loading="loading" @click="refresh">重新查询状态</el-button></div></div>
    <el-skeleton v-if="loading && !record" :rows="8" animated />
    <template v-else-if="record">
      <el-card shadow="never" class="card"><template #header><div class="card-title">基本信息 <el-tag :type="statusMeta(version?.status).type">{{ statusMeta(version?.status).text }}</el-tag></div></template><el-descriptions :column="2" border><el-descriptions-item label="内部案例编号">{{ record.internalCode }}</el-descriptions-item><el-descriptions-item label="案例类型">{{ record.caseType }}</el-descriptions-item><el-descriptions-item label="教学难度">{{ record.difficulty }}</el-descriptions-item><el-descriptions-item label="课程标签"><el-tag v-for="tag in record.courseTags" :key="tag" class="tag">{{ tag }}</el-tag></el-descriptions-item><el-descriptions-item label="有效期">{{ record.validUntil || '长期有效' }}</el-descriptions-item><el-descriptions-item label="脱敏等级">{{ record.desensitizationLevel }}</el-descriptions-item><el-descriptions-item label="文件信息" :span="2">{{ record.file?.fileName || '尚未上传' }} <span class="muted">{{ formatBytes(record.file?.fileSize) }}</span></el-descriptions-item><el-descriptions-item label="创建时间" :span="2">{{ formatDate(record.createdAt) }}</el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="card"><template #header><div class="card-title">转换版本</div></template><el-empty v-if="!version" description="尚未创建转换版本" /><template v-else><el-progress v-if="version.status === 'PROCESSING'" :percentage="version.progress || 0" status="warning" /><el-descriptions :column="2" border class="version-data"><el-descriptions-item label="版本状态"><el-tag :type="statusMeta(version.status).type">{{ statusMeta(version.status).text }}</el-tag></el-descriptions-item><el-descriptions-item label="版本创建时间">{{ formatDate(version.createdAt) }}</el-descriptions-item><el-descriptions-item label="点数">{{ version.pointCount?.toLocaleString() || '-' }}</el-descriptions-item><el-descriptions-item label="边界范围">{{ formatBounds(version.bounds) }}</el-descriptions-item><el-descriptions-item v-if="version.failureReason" label="失败错误信息" :span="2"><span class="failure">{{ version.failureReason }}</span></el-descriptions-item></el-descriptions></template></el-card>
      <el-alert v-if="version?.status === 'PROCESSING'" title="点云转换处理中" description="转换完成后可进入三维工作台。" type="warning" :closable="false" show-icon />
      <el-alert v-else-if="version?.status === 'FAILED'" title="点云转换失败" :description="version.failureReason || '请检查转换任务后重试。'" type="error" :closable="false" show-icon />
      <el-button v-else-if="version?.status === 'READY'" type="primary" @click="router.push(`/admin/cases/${record.id}/viewer`)">进入三维工作台</el-button>
    </template>
  </main>
</template>

<style scoped>
.page-shell { max-width: 1180px; min-height: 100vh; margin: 0 auto; padding: 36px 32px; }.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.header-actions { display: flex; gap: 12px; }.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }h1 { margin: 0; color: #142d4d; font-size: 27px; }.page-description { margin: 10px 0 0; color: #718096; }.card { margin-bottom: 20px; }.card-title { display: flex; align-items: center; justify-content: space-between; }.tag { margin-right: 6px; }.muted { margin-left: 8px; color: #8491a3; }.version-data { margin-top: 18px; }.failure { color: #c45656; }@media (max-width: 720px) { .page-shell { padding: 24px 16px; }.page-header { flex-direction: column; }.header-actions { width: 100%; }.header-actions .el-button { flex: 1; } }
</style>
