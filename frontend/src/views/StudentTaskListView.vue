<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudentTasks } from '@/api/student'
import type { StudentTask } from '@/types/student'
import { displayTime, taskStatus } from '@/utils/student'

const tasks = ref<StudentTask[]>([]); const loading = ref(false)
async function load(){ loading.value=true; try { tasks.value=await getStudentTasks() } catch(e) { ElMessage.error(e instanceof Error?e.message:'任务加载失败') } finally { loading.value=false } }
onMounted(load)
</script>
<template><main class="page"><div class="head"><div><p>学生 / 我的实训</p><h1>我的实训任务</h1></div><el-button @click="load">刷新</el-button></div><el-card shadow="never"><el-table :data="tasks" v-loading="loading"><el-table-column prop="name" label="任务名称" min-width="180"/><el-table-column prop="caseName" label="案例名称" min-width="160"/><el-table-column label="开始/截止时间" min-width="300"><template #default="{row}">{{ displayTime(row.startAt) }}<br><span class="muted">截止：{{ displayTime(row.dueAt) }}</span></template></el-table-column><el-table-column label="状态" width="110"><template #default="{row}"><el-tag :type="taskStatus(row.status)[1]">{{ taskStatus(row.status)[0] }}</el-tag></template></el-table-column><el-table-column label="允许迟交" width="100"><template #default="{row}">{{ row.allowLate?'是':'否' }}</template></el-table-column><el-table-column label="操作" width="130" fixed="right"><template #default="{row}"><el-button link type="primary" @click="$router.push(`/student/tasks/${row.id}`)">{{ row.status==='SUBMITTED'?'查看提交':'进入实训' }}</el-button></template></el-table-column></el-table><el-empty v-if="!loading&&!tasks.length" description="暂无实训任务"/></el-card></main></template>
<style scoped>.page{max-width:1440px;min-height:100vh;margin:auto;padding:36px 32px}.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.head p{margin:0;color:#64748b;font-size:13px}h1{margin:7px 0;font-size:27px;color:#142d4d}.muted{color:#8491a3;font-size:12px}@media(max-width:720px){.page{padding:24px 16px}}</style>
