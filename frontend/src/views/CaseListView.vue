<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCases } from '@/api/cases'
import type { CaseRecord } from '@/types/case'
import { formatBounds, formatBytes, formatDate, statusMeta } from '@/utils/case'

const loading = ref(false)
const records = ref<CaseRecord[]>([])

async function loadCases() {
  loading.value = true
  try { records.value = (await getCases()).items }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '案例列表加载失败') }
  finally { loading.value = false }
}

onMounted(loadCases)
</script>

<template>
  <main class="page-shell">
    <div class="page-header">
      <div><p class="eyebrow">管理员 / 案例管理</p><h1>案例导入与转换</h1><p class="page-description">创建教学案例并导入 LAS 或 LAZ 文件，跟踪转换处理状态。</p></div>
      <div class="header-actions"><el-button @click="loadCases">刷新</el-button><el-button type="primary" @click="$router.push('/admin/cases/new')">创建案例</el-button></div>
    </div>
    <el-card shadow="never">
      <el-table v-loading="loading" :data="records" row-key="id" min-width="1200">
        <el-table-column label="教学标题" min-width="190"><template #default="{ row }"><strong>{{ row.teachingTitle }}</strong><div class="subtext">{{ row.caseType }} · {{ row.difficulty }}</div></template></el-table-column>
        <el-table-column prop="internalCode" label="案例编号" min-width="140" />
        <el-table-column label="文件" min-width="180"><template #default="{ row }"><span>{{ row.file?.fileName || '尚未上传' }}</span><div class="subtext">{{ formatBytes(row.file?.fileSize) }}</div></template></el-table-column>
        <el-table-column label="版本状态" width="110"><template #default="{ row }"><el-tag :type="statusMeta(row.latestVersion?.status).type">{{ statusMeta(row.latestVersion?.status).text }}</el-tag></template></el-table-column>
        <el-table-column label="点数 / 边界范围" min-width="260"><template #default="{ row }"><div>{{ row.latestVersion?.pointCount?.toLocaleString() || '-' }}</div><div class="subtext">{{ formatBounds(row.latestVersion?.bounds) }}</div></template></el-table-column>
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.createdAt) }}</template></el-table-column>
        <el-table-column label="失败原因" min-width="150"><template #default="{ row }"><span class="failure">{{ row.latestVersion?.failureReason || '-' }}</span></template></el-table-column>
        <el-table-column label="操作" fixed="right" width="100"><template #default="{ row }"><el-button link type="primary" @click="$router.push(`/admin/cases/${row.id}`)">查看详情</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && records.length === 0" description="暂无案例，请先创建案例" />
    </el-card>
  </main>
</template>

<style scoped>
.page-shell { max-width: 1440px; min-height: 100vh; margin: 0 auto; padding: 36px 32px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 24px; }.header-actions { display: flex; flex: none; gap: 12px; }
.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }h1 { margin: 0; color: #142d4d; font-size: 27px; }.page-description { margin: 10px 0 0; color: #718096; }.subtext { margin-top: 5px; color: #8491a3; font-size: 12px; line-height: 1.35; }.failure { color: #c45656; }
@media (max-width: 720px) { .page-shell { padding: 24px 16px; }.page-header { flex-direction: column; }.header-actions { width: 100%; }.header-actions .el-button { flex: 1; } }
</style>
