<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api/teacher'
import type { Course, TeachingTask } from '@/types/teacher'
const list=ref<TeachingTask[]>([]), courses=ref<Course[]>([]), courseId=ref(''), status=ref(''), busy=ref(false)
const labels:Record<string,string>={DRAFT:'草稿',PUBLISHED:'已发布',CLOSED:'已关闭'}
async function load(){busy.value=true;try{list.value=await api.tasks(courseId.value,status.value)}catch(e){ElMessage.error(api.message(e))}finally{busy.value=false}}
onMounted(async()=>{try{courses.value=await api.courses();await load()}catch(e){ElMessage.error(api.message(e))}})
</script>
<template><main class="teacher-page"><header><h1>教学任务</h1><el-button @click="$router.push('/teacher/courses')">课程管理</el-button><el-button type="primary" @click="$router.push('/teacher/tasks/new')">创建任务</el-button></header><div class="actions"><el-select v-model="courseId" clearable placeholder="全部课程" style="width:240px" @change="load"><el-option v-for="c in courses" :key="c.id" :value="c.id" :label="c.name"/></el-select><el-select v-model="status" clearable placeholder="全部状态" style="width:160px" @change="load"><el-option v-for="(label,value) in labels" :key="value" :value="value" :label="label"/></el-select><el-button @click="load">刷新</el-button></div><el-table :data="list" v-loading="busy"><el-table-column prop="title" label="任务"/><el-table-column label="状态"><template #default="{row}">{{labels[row.status]}}</template></el-table-column><el-table-column label="提交进度"><template #default="{row}">{{row.submittedCount}} / {{row.assignedCount}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="$router.push(`/teacher/tasks/${row.id}`)">详情 / 批改</el-button></template></el-table-column></el-table><el-empty v-if="!busy&&!list.length" description="暂无教学任务"/></main></template>
