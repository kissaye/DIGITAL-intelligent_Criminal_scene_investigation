<script setup lang="ts">
import { ref } from 'vue'
import GlobalNav from '@/components/GlobalNav.vue'
import ProductVisual from '@/components/ProductVisual.vue'
import LoginPanel from '@/components/LoginPanel.vue'
import ScrollReveal from '@/components/ScrollReveal.vue'
const panelOpen=ref(false),busy=ref(false),panel=ref<InstanceType<typeof LoginPanel>>()
function scrollTo(id:string){document.getElementById(id)?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}
function closePanel(done:()=>void){if(!busy.value)done()}
</script>
<template>
  <GlobalNav @enter="panelOpen=true" @section="scrollTo"/>
  <main class="product-page">
    <section class="product-hero"><ScrollReveal immediate><p class="product-label">数智刑勘</p><h1>让真实现场，<br>成为可控的教学空间。</h1><p class="summary">从三维现场、数据脱敏到教学实训，<br>在一套可信流程中自然连接。</p><div class="actions"><el-button type="primary" round @click="panelOpen=true">进入平台</el-button><button @click="scrollTo('capabilities')">了解平台能力</button></div><ProductVisual variant="hero"/></ScrollReveal></section>
    <section id="capabilities" class="story"><ScrollReveal><p class="product-label">从现场，到课堂</p><h2>真实数据进入教学，<br>需要的不只是上传。</h2><p>将离线点云转化为有授权、有边界、可复核的教学资源。</p><ol class="chain"><li>离线导入</li><li>受控存储</li><li>脱敏复核</li><li>教学发布</li><li>实训任务</li></ol></ScrollReveal></section>
    <section class="story dark"><ScrollReveal><h2>现场，被完整保留。</h2><p>旋转、缩放、标记、测距与空间复核，<br>让复杂现场在浏览器中清晰呈现。</p><ProductVisual variant="viewer"/></ScrollReveal></section>
    <section id="security" class="story"><ScrollReveal><p class="product-label">清晰的安全边界</p><h2>该隐藏的，<br>始终不会暴露。</h2><p>HIDE 强制遮挡与 DELETE 派生删除各有明确职责。<br>授权有效期、教学副本和访问审计，让教学使用有据可查。</p><ProductVisual variant="security"/></ScrollReveal></section>
    <section id="education" class="story roles"><ScrollReveal><article><p>管理员</p><h2>准备可信教学案例。</h2><p>沿版本谱系，完成导入、复核、授权与发布。</p><ProductVisual variant="lineage"/></article></ScrollReveal><ScrollReveal><article><p>教师</p><h2>把勘验流程带进课堂。</h2><p>组织课程与班级，布置实训，查看提交并给出反馈。</p><button @click="panelOpen=true">进入教学工作台</button></article></ScrollReveal><ScrollReveal><article><p>学生</p><h2>让观察形成判断。</h2><p>浏览受控现场、标记与测量，让勘验过程沉淀为笔录。</p><button @click="panelOpen=true">进入实训工作台</button></article></ScrollReveal></section>
    <section class="story final"><ScrollReveal><h2>让下一次实训，<br>从真实现场开始。</h2><el-button type="primary" size="large" @click="panelOpen=true">进入平台</el-button></ScrollReveal></section>
  </main>
  <el-dialog v-model="panelOpen" class="product-login-dialog" title="登录数智刑勘" width="min(438px, calc(100vw - 32px))" align-center :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy" :before-close="closePanel" @opened="panel?.focusUsername()"><LoginPanel ref="panel" @busy="busy=$event"/></el-dialog>
</template>
<style scoped>
.product-page{background:#fff}.product-hero{max-width:1100px;margin:auto;padding:44px 24px 72px;text-align:center}.product-label{font-size:17px;font-weight:600;color:#6e6e73}.product-hero h1{font-size:clamp(38px,5.1vw,72px);line-height:1.12;letter-spacing:-.045em;margin:16px 0}.summary{font-size:20px;line-height:1.6;color:#6e6e73;margin:22px 0}.actions{display:flex;justify-content:center;gap:24px;align-items:center;margin:24px 0 38px}.actions>button:last-child,.roles button{border:0;background:none;color:#0071e3;cursor:pointer}.story{padding:110px max(24px,calc((100vw - 1040px)/2));background:#f5f5f7;scroll-margin-top:48px}.story h2{font-size:clamp(34px,4.7vw,60px);line-height:1.15;letter-spacing:-.04em;margin:12px 0 28px}.story p{font-size:19px;line-height:1.65;color:#6e6e73}.story .product-visual{margin-top:50px}.chain{display:flex;gap:25px;justify-content:space-between;padding:36px 0 0;list-style:none;font-size:17px;border-top:1px solid #00000012;margin:55px 0 0}.dark{background:#000;color:#fff}.dark p{color:#a1a1a6}.roles{background:#fff}.roles article{padding:45px 0;border-bottom:1px solid #00000010}.roles .scroll-reveal:nth-child(2){text-align:right}.roles button{padding:12px 0;font-size:16px}.final{text-align:center;background:#fff}
@media(min-width:1600px){.product-hero{padding-top:70px}.product-hero .product-visual{margin-top:44px}}
@media(min-width:701px) and (max-height:800px){.product-hero{padding-top:24px}.product-hero h1{font-size:60px;font-weight:650}.product-label{margin:10px 0}.summary{font-size:18px;margin:16px 0}.actions{margin:18px 0 28px}.product-hero :deep(svg){max-height:260px}.product-hero :deep(.visual-bar){padding:12px 26px}.product-hero :deep(figcaption){padding-bottom:14px}}
@media(max-width:600px){.product-hero{padding-top:35px}.summary{font-size:17px}.story{padding:70px 24px}.chain{flex-direction:column;gap:20px}.actions{gap:12px}.roles .scroll-reveal:nth-child(2){text-align:left}}
@media(max-width:420px){.product-hero h1{font-size:34px}}
</style>
<style>.product-login-dialog{max-height:calc(100dvh - 32px);overflow-y:auto;padding:24px!important}.product-login-dialog .el-dialog__header{padding-bottom:12px}.product-login-dialog .el-dialog__body{padding:0}</style>
