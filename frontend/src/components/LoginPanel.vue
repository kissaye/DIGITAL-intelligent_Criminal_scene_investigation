<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { ElMessage, type FormInstance, type InputInstance } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { homeRouteForRoles } from '@/utils/auth'
const emit = defineEmits<{ busy: [value: boolean] }>()
const router = useRouter(), route = useRoute(), auth = useAuthStore()
const form = ref({ username: '', password: '' }), formRef = ref<FormInstance>(), usernameInput = ref<InputInstance>()
const loading = ref(false), errorText = ref('')
const mock = import.meta.env.VITE_USE_MOCK !== 'false'
async function focusUsername() { await nextTick(); usernameInput.value?.focus() }
async function submit() {
  if (loading.value) return
  loading.value = true; emit('busy', true); errorText.value = ''
  try {
    if (!await formRef.value?.validate().catch(() => false)) return
    await auth.login(form.value.username, form.value.password)
    ElMessage.success('登录成功')
    await router.replace(typeof route.query.redirect === 'string' ? route.query.redirect : homeRouteForRoles(auth.user?.roles))
  } catch(error) { errorText.value = error instanceof Error ? error.message : '登录失败，请检查用户名或密码' }
  finally { loading.value = false; emit('busy', false) }
}
defineExpose({ focusUsername })
</script>
<template><div class="login-panel"><p class="panel-label">DIGITAL FORENSICS EDUCATION</p><p class="panel-intro">以你的角色，继续现场中的工作。</p><el-alert v-if="errorText" :title="errorText" type="error" :closable="false" show-icon/><el-form ref="formRef" :model="form" label-position="top" :disabled="loading" @submit.prevent="submit"><el-form-item label="用户名" prop="username" :rules="[{required:true,message:'请输入用户名',trigger:'blur'}]"><el-input ref="usernameInput" v-model="form.username" aria-label="用户名" autocomplete="username" placeholder="请输入用户名"/></el-form-item><el-form-item label="密码" prop="password" :rules="[{required:true,message:'请输入密码',trigger:'blur'}]"><el-input v-model="form.password" aria-label="密码" type="password" show-password autocomplete="current-password" placeholder="请输入密码"/></el-form-item><el-button type="primary" native-type="submit" :loading="loading" :disabled="loading" class="submit">{{loading?'登录中…':'登录'}}</el-button></el-form><p v-if="mock" class="mock-hint">演示模式：用户名包含 admin、teacher 或其他名称，分别进入管理员、教师或学生工作台。密码填写任意非空内容。</p></div></template>
<style scoped>
.login-panel { padding: 4px 12px 14px; }.panel-label { margin: 12px 0; color:#0071e3; font-size:10px; letter-spacing:.08em; }.panel-intro { color:#6e6e73; margin:0 0 28px; line-height:1.6; }.submit { width:100%; min-height:44px; }.mock-hint { font-size:12px; line-height:1.7; color:#6e6e73; margin:20px 0 0; }.el-alert { margin-bottom:18px; }
</style>
