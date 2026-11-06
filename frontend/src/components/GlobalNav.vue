<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Menu, Close } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const props=defineProps<{signedIn?:boolean}>()
const emit=defineEmits<{enter:[];capabilities:[];section:[id:string]}>()
const router=useRouter(),auth=useAuthStore(),open=ref(false),toggle=ref<HTMLButtonElement>()
const user=computed(()=>auth.user?.displayName||auth.user?.username||'管理员')
function close(){open.value=false}
function escape(event:KeyboardEvent){if(event.key==='Escape'&&open.value){close();toggle.value?.focus()}}
window.addEventListener('keydown',escape)
onBeforeUnmount(()=>window.removeEventListener('keydown',escape))
function section(id:string){close();emit('section',id);if(id==='capabilities')emit('capabilities')}
async function logout(){close();auth.clear();await router.replace('/login')}
</script>
<template><header class="global-nav"><nav aria-label="产品导航"><router-link class="wordmark" :to="signedIn?'/admin':'/login'" @click="close">数智刑勘<span>DIGITAL FORENSICS</span></router-link><button ref="toggle" class="mobile-toggle" :aria-expanded="open" aria-controls="product-menu" aria-label="展开或关闭导航" @click="open=!open"><el-icon><Close v-if="open"/><Menu v-else/></el-icon></button><div id="product-menu" class="links" :class="{open}"><template v-if="props.signedIn"><router-link to="/admin/cases" @click="close">案例</router-link><router-link to="/admin/cases/new" @click="close">导入</router-link><button @click="section('publication-story')">发布与审计</button><router-link class="user" to="/admin" @click="close">{{user}}</router-link><button @click="logout">退出登录</button></template><template v-else><button @click="section('capabilities')">平台能力</button><button @click="section('education')">教学实训</button><button @click="section('security')">数据安全</button><button class="enter" @click="close();emit('enter')">进入平台</button></template></div></nav></header></template>
<style scoped>
.global-nav{position:sticky;top:0;height:48px;background:#fffffff0;border-bottom:1px solid #00000008;z-index:30;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}nav{display:flex;align-items:center;gap:30px;max-width:1160px;height:100%;margin:auto;padding:0 24px}.links{display:flex;align-items:center;gap:28px}button,a{border:0;background:none;color:#59595f;text-decoration:none;font-size:12px;cursor:pointer}.wordmark{margin-right:auto;color:#1d1d1f;font-size:16px;font-weight:650;white-space:nowrap}.wordmark span{margin-left:12px;font-size:8px;font-weight:500;letter-spacing:.09em;color:#818187}.enter,.user{color:#0071e3}.mobile-toggle{display:none;font-size:21px}.links a:hover,.links button:hover{color:#0071e3}button:focus-visible,a:focus-visible{outline:3px solid #0071e355;outline-offset:5px;border-radius:4px}@media(max-width:700px){.wordmark span{display:none}.mobile-toggle{display:block}.links{display:none;position:absolute;top:48px;left:0;right:0;padding:24px;background:#fff;border-bottom:1px solid #e5e5e7;flex-direction:column;align-items:stretch;gap:0}.links.open{display:flex}.links a,.links button{padding:14px 8px;text-align:left;font-size:16px}}@supports not (backdrop-filter:blur(1px)){.global-nav{background:#fff}}
</style>
