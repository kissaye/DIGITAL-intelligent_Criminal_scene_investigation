<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, type FormInstance, type UploadFile, type UploadUserFile } from 'element-plus'
import { useRouter } from 'vue-router'
import { createCase, createCaseVersion, uploadCaseFile } from '@/api/cases'
import { formatBytes } from '@/utils/case'

const router = useRouter()
const formRef = ref<FormInstance>()
const creating = ref(false)
const selectedFile = ref<File | null>(null)
const fileList = ref<UploadUserFile[]>([])
const maxFileSize = 2 * 1024 * 1024 * 1024
const form = ref({ internalCode: '', teachingTitle: '', caseType: '', difficulty: '', courseTags: [] as string[], validUntil: '', desensitizationLevel: '' })
const fileSummary = computed(() => selectedFile.value ? `${selectedFile.value.name}（${formatBytes(selectedFile.value.size)}）` : '')

function selectFile(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!['las', 'laz'].includes(extension || '')) { ElMessage.error('仅支持上传 .las 或 .laz 点云文件'); removeFile(); return }
  if (file.size > maxFileSize) { ElMessage.error('文件超过 2 GB，请压缩或联系管理员后重试'); removeFile(); return }
  selectedFile.value = file
  fileList.value = [{ name: file.name, size: file.size, status: 'ready', uid: Date.now() }]
}

function removeFile() { selectedFile.value = null; fileList.value = [] }

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!selectedFile.value) { ElMessage.warning('请选择需要上传的 LAS 或 LAZ 文件'); return }
  creating.value = true
  try {
    const record = await createCase(form.value)
    const uploadedFile = await uploadCaseFile(record.id, selectedFile.value)
    await createCaseVersion(record.id, uploadedFile.id)
    ElMessage.success('案例已创建，正在进行转换处理')
    await router.replace(`/admin/cases/${record.id}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建或上传失败，请稍后重试')
  } finally { creating.value = false }
}
</script>

<template>
  <main class="page-shell narrow">
    <div class="page-header"><div><p class="eyebrow">管理员 / 案例管理</p><h1>创建案例</h1><p class="page-description">按“创建案例 → 上传文件 → 创建转换版本”的顺序提交。</p></div><el-button @click="router.push('/admin/cases')">返回列表</el-button></div>
    <el-card shadow="never">
      <el-form ref="formRef" :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="内部案例编号" prop="internalCode" :rules="[{ required: true, message: '请输入内部案例编号', trigger: 'blur' }]"><el-input v-model="form.internalCode" placeholder="例如 CASE-2026-001" :disabled="creating" /></el-form-item>
          <el-form-item label="教学标题" prop="teachingTitle" :rules="[{ required: true, message: '请输入教学标题', trigger: 'blur' }]"><el-input v-model="form.teachingTitle" placeholder="面向教学展示的案例名称" :disabled="creating" /></el-form-item>
          <el-form-item label="案例类型" prop="caseType" :rules="[{ required: true, message: '请选择案例类型', trigger: 'change' }]"><el-select v-model="form.caseType" placeholder="请选择" :disabled="creating"><el-option label="盗窃" value="盗窃" /><el-option label="入室" value="入室" /><el-option label="交通事故" value="交通事故" /><el-option label="其他" value="其他" /></el-select></el-form-item>
          <el-form-item label="教学难度" prop="difficulty" :rules="[{ required: true, message: '请选择教学难度', trigger: 'change' }]"><el-select v-model="form.difficulty" placeholder="请选择" :disabled="creating"><el-option label="基础" value="基础" /><el-option label="进阶" value="进阶" /><el-option label="综合" value="综合" /></el-select></el-form-item>
          <el-form-item label="课程标签" prop="courseTags" :rules="[{ required: true, message: '请至少添加一个课程标签', trigger: 'change' }]"><el-select v-model="form.courseTags" multiple filterable allow-create default-first-option placeholder="可输入并回车创建标签" :disabled="creating"><el-option label="现场勘查" value="现场勘查" /><el-option label="刑事技术" value="刑事技术" /><el-option label="证据分析" value="证据分析" /></el-select></el-form-item>
          <el-form-item label="有效期"><el-date-picker v-model="form.validUntil" type="date" value-format="YYYY-MM-DD" placeholder="不填表示长期有效" :disabled="creating" /></el-form-item>
          <el-form-item label="脱敏等级" prop="desensitizationLevel" :rules="[{ required: true, message: '请选择脱敏等级', trigger: 'change' }]"><el-select v-model="form.desensitizationLevel" placeholder="请选择" :disabled="creating"><el-option label="一级" value="一级" /><el-option label="二级" value="二级" /><el-option label="三级" value="三级" /></el-select></el-form-item>
        </div>
        <el-form-item label="点云文件" required><el-upload :auto-upload="false" :limit="1" :file-list="fileList" accept=".las,.laz" :on-change="selectFile" :on-remove="removeFile" :disabled="creating"><el-button :disabled="creating">选择 LAS / LAZ 文件</el-button><template #tip><div class="el-upload__tip">仅支持 .las、.laz，单个文件不超过 2 GB；不在页面展示原始存储路径。</div></template></el-upload><p v-if="fileSummary" class="file-summary">待上传：{{ fileSummary }}</p></el-form-item>
        <el-alert title="提交后将创建转换版本，处理完成前请勿重复提交。" type="info" :closable="false" show-icon />
        <div class="form-actions"><el-button @click="router.push('/admin/cases')" :disabled="creating">取消</el-button><el-button type="primary" :loading="creating" @click="submit">{{ creating ? '正在提交…' : '创建并上传' }}</el-button></div>
      </el-form>
    </el-card>
  </main>
</template>

<style scoped>
.page-shell { min-height: 100vh; margin: 0 auto; padding: 36px 32px; }.narrow { max-width: 1080px; }.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }h1 { margin: 0; color: #142d4d; font-size: 27px; }.page-description { margin: 10px 0 0; color: #718096; }.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 24px; }.el-select, .el-date-editor { width: 100%; }.file-summary { margin: 10px 0 0; color: #4c617a; }.form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 28px; }@media (max-width: 720px) { .page-shell { padding: 24px 16px; }.page-header { flex-direction: column; }.form-grid { grid-template-columns: 1fr; } }
</style>
