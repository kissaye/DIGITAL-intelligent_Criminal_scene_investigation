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
<template>
  <main class="task-page">
    <header><div><p>学生 / 实训</p><h1>我的实训任务</h1></div><el-button :loading="loading" @click="load">刷新</el-button></header>
    <section v-loading="loading" aria-label="任务列表">
      <article v-for="task in tasks" :key="task.id">
        <div><el-tag size="small" :type="taskStatus(task.status)[1]">{{ taskStatus(task.status)[0] }}</el-tag>
          <h2>{{ task.name }}</h2><p>{{ task.caseName }}</p>
          <small>开始 {{ displayTime(task.startAt) }} · 截止 {{ displayTime(task.dueAt) }} · {{ task.allowLate ? '允许迟交' : '不允许迟交' }}</small>
        </div>
        <el-button :type="task.status === 'IN_PROGRESS' ? 'primary' : 'default'" @click="$router.push(`/student/tasks/${task.id}`)">{{ task.status === 'SUBMITTED' ? '查看提交' : task.status === 'IN_PROGRESS' ? '进入实训' : '查看任务' }}</el-button>
      </article>
      <el-empty v-if="!loading && !tasks.length" description="暂无实训任务" />
    </section>
  </main>
</template>
<style scoped>
header, article { display:flex; justify-content:space-between; align-items:center; gap:20px; flex-wrap:wrap; }
header { margin-bottom:32px; }
h1 { font-size:clamp(30px,4vw,44px); margin:0; }
h2 { margin:12px 0 0; }
p, small { color:#6e6e73; line-height:1.65; }
section { background:white; border-radius:20px; padding:0 24px; }
article { padding:24px 0; border-bottom:1px solid #00000010; }
article:last-child { border-bottom:0; }
</style>
