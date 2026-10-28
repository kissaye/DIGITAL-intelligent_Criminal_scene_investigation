<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { homeRouteForRoles } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const formRef = ref()

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : homeRouteForRoles(auth.user?.roles)
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <el-card class="login-card" shadow="always">
      <p class="eyebrow">DIGITAL INTELLIGENT CRIMINAL SCENE INVESTIGATION</p>
      <h1>数智刑勘平台</h1>
      <p class="subtitle">登录后进入对应角色的工作台</p>
      <el-form ref="formRef" :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" prop="username" :rules="[{ required: true, message: '请输入用户名', trigger: 'blur' }]">
          <el-input v-model="form.username" autocomplete="username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password" :rules="[{ required: true, message: '请输入密码', trigger: 'blur' }]">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="submit-button">{{ loading ? '登录中...' : '登录' }}</el-button>
      </el-form>
      <p class="mock-hint">Mock 模式：用户名含 admin、teacher 或其他名称，分别进入管理员、教师或学生首页。</p>
    </el-card>
  </main>
</template>

<style scoped>
.login-page { display: grid; min-height: 100vh; padding: 24px; place-items: center; background: radial-gradient(circle at top, #e8f1fc 0, #f5f8fc 42%, #eef2f8 100%); }
.login-card { width: min(100%, 420px); border: 0; border-top: 4px solid #1667c7; }
.eyebrow { margin: 2px 0 12px; color: #5b6b82; font-size: 11px; letter-spacing: .08em; }
h1 { margin: 0; color: #142d4d; font-size: 28px; }
.subtitle { margin: 10px 0 24px; color: #708096; }
.submit-button { width: 100%; margin-top: 8px; }
.mock-hint { margin: 20px 0 0; color: #8b97a9; font-size: 12px; line-height: 1.6; }
</style>
