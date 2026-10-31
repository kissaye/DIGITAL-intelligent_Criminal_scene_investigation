<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { roleLabel } from '@/utils/auth'

const mock = import.meta.env.VITE_USE_MOCK !== 'false'
const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)
const roles = computed(() => roleLabel(user.value?.roles))
const isAdmin = computed(() => user.value?.roles.includes('ADMIN'))
const isTeacher = computed(() => user.value?.roles.includes('TEACHER'))
const isStudent = computed(() => user.value?.roles.includes('STUDENT'))

async function logout() {
  auth.clear()
  await router.replace('/login')
}
</script>

<template>
  <main class="home-page">
    <el-card class="home-card">
      <div class="topline">
        <div><p class="eyebrow">数智刑勘平台</p><h1>{{ roles }}首页</h1></div>
        <el-button plain @click="logout">退出登录</el-button>
      </div>
      <el-alert v-if="isTeacher && mock" title="模拟模式：教师数据仅保存在本浏览器，查找学生使用 student；真实任务分配和批改请设置 VITE_USE_MOCK=false。" type="warning" :closable="false"/>
      <el-divider />
      <p>当前用户：<strong>{{ user?.displayName || user?.username }}</strong></p>
      <p>当前角色：<el-tag type="primary">{{ roles }}</el-tag></p>
      <el-button v-if="isAdmin" type="primary" @click="router.push('/admin/cases')">案例管理</el-button>
      <el-button v-if="isStudent" type="primary" @click="router.push('/student/tasks')">我的实训任务</el-button>
      <el-button v-if="isTeacher" type="primary" @click="router.push('/teacher/courses')">课程管理</el-button>
      <el-button v-if="isTeacher" @click="router.push('/teacher/tasks')">教学任务</el-button>
      <el-empty description="模块开发中" :image-size="100" />
    </el-card>
  </main>
</template>

<style scoped>
.home-page { min-height: 100vh; padding: 48px 24px; background: #f4f7fb; }
.home-card { max-width: 760px; margin: 0 auto; }
.topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }
h1 { margin: 0; color: #142d4d; font-size: 25px; }
</style>
