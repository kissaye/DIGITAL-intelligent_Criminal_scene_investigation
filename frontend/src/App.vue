<script setup lang="ts">
import { computed, ref } from 'vue'
import { Fold, Expand, SwitchButton } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { roleLabel } from '@/utils/auth'
type MenuItem={path:string;label:string;matches:(path:string)=>boolean}
const route=useRoute(),router=useRouter(),auth=useAuthStore(),collapsed=ref(false)
const roles=computed(()=>auth.user?.roles||[]),name=computed(()=>auth.user?.displayName||auth.user?.username||'用户')
const standalone=computed(()=>route.path==='/login'||route.meta.fullscreen===true||route.meta.productPage===true)
const menus=computed<MenuItem[]>(()=>roles.value.includes('ADMIN')?[{path:'/admin',label:'总览',matches:p=>p==='/admin'},{path:'/admin/cases',label:'案例管理',matches:p=>p.startsWith('/admin/cases')}]:roles.value.includes('TEACHER')?[{path:'/teacher',label:'总览',matches:p=>p==='/teacher'},{path:'/teacher/courses',label:'课程与班级',matches:p=>p.startsWith('/teacher/courses')},{path:'/teacher/tasks',label:'实训任务',matches:p=>p.startsWith('/teacher/tasks')}]:[{path:'/student',label:'总览',matches:p=>p==='/student'},{path:'/student/tasks',label:'我的实训',matches:p=>p.startsWith('/student/tasks')}])
const active=computed(()=>menus.value.find(item=>item.matches(route.path))?.path),pageTitle=computed(()=>menus.value.find(item=>item.matches(route.path))?.label||`${roleLabel(roles.value)}工作台`)
async function logout(){auth.clear();await router.replace('/login')}
</script>
<template><router-view v-if="standalone"/><div v-else class="app-shell" :class="{collapsed}"><aside class="side-nav"><button class="brand" aria-label="返回工作台" @click="router.push(menus[0]?.path)"><span class="brand-mark">DF</span><span class="brand-copy">数智刑勘<small>DIGITAL FORENSICS EDUCATION</small></span></button><nav aria-label="主菜单"><button v-for="item in menus" :key="item.path" :class="{active:active===item.path}" @click="router.push(item.path)"><span class="nav-dot"/> <span class="nav-label">{{item.label}}</span></button></nav><div class="account"><span class="avatar">{{name.slice(0,1)}}</span><div class="account-copy"><b>{{name}}</b><small>{{roleLabel(roles)}}</small></div><el-button class="logout" link :icon="SwitchButton" aria-label="退出登录" @click="logout"/></div><el-button class="collapse" text :icon="collapsed?Expand:Fold" :aria-label="collapsed?'展开导航':'收起导航'" @click="collapsed=!collapsed"/></aside><section class="app-main"><header class="topbar"><strong>{{pageTitle}}</strong><span class="topbar-note">刑侦产教融合平台</span></header><div class="content"><router-view/></div></section></div></template>
