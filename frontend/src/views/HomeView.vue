<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { roleLabel } from '@/utils/auth'

const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)
const roles = computed(() => roleLabel(user.value?.roles))

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
      <el-divider />
      <p>当前用户：<strong>{{ user?.displayName || user?.username }}</strong></p>
      <p>当前角色：<el-tag type="primary">{{ roles }}</el-tag></p>
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
