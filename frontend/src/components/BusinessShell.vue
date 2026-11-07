<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import GlobalNav from './GlobalNav.vue'
const router=useRouter()
const route=useRoute()
const titles: Record<string,string> = {'admin-case-new':'案例导入','admin-case-detail':'案例详情','admin-case-publication':'发布与审计','teacher-courses':'课程与班级','teacher-tasks':'实训任务','teacher-submissions':'提交与评分','student-tasks':'我的实训'}
</script>
<template><div class="business-shell"><GlobalNav signed-in @section="router.push('/admin#publication-story')"/><div class="business-content"><p v-if="titles[String(route.name)]" class="business-context">{{titles[String(route.name)]}}</p><slot/></div></div></template>
<style scoped>.business-shell{min-height:100vh;background:#f5f5f7}.business-content{max-width:1440px;margin:auto;padding:60px 48px 80px;min-width:0}@media(max-width:700px){.business-content{padding:38px 20px 64px}}.business-context{color:#6e6e73;font-size:12px;margin:0 0 16px}.business-content :deep(.page),.business-content :deep(.page-shell){padding:0;min-height:0}.business-content :deep(.head),.business-content :deep(.page-header){flex-wrap:wrap;gap:14px}.business-content :deep(h1){font-size:clamp(30px,4vw,44px)}.business-content :deep(.el-card),.business-content :deep(.el-table){min-width:0;max-width:100%}.business-content :deep(.el-drawer){max-width:100vw}</style>
