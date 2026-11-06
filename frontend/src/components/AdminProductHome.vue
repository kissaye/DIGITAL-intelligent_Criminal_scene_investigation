<script setup lang="ts">
import { useRouter } from 'vue-router'
import GlobalNav from './GlobalNav.vue'
import ProductVisual from './ProductVisual.vue'
import ScrollReveal from './ScrollReveal.vue'
const router=useRouter()
function section(id:string){document.getElementById(id)?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}
</script>
<template><GlobalNav signed-in @section="section"/><main class="admin-product"><section class="hero"><ScrollReveal immediate><p class="eyebrow">管理员 · 案例生命周期</p><h1>每一个教学现场，<br>都经过可信处理。</h1><p class="summary">从案例导入、脱敏复核到版本发布，<br>让现场数据安全走向教学使用。</p><div class="actions"><el-button type="primary" size="large" @click="router.push('/admin/cases/new')">导入新案例</el-button><el-button text type="primary" @click="router.push('/admin/cases')">查看案例</el-button></div><ProductVisual variant="lineage"/></ScrollReveal></section><section class="chapters"><ScrollReveal><article><p>01 / 准备</p><h2>案例导入与转换。</h2><p>从离线点云建立案例，在处理状态中确认每一步。</p><el-button text type="primary" @click="router.push('/admin/cases/new')">导入新案例</el-button></article></ScrollReveal><ScrollReveal><article class="review"><div><p>02 / 复核</p><h2>脱敏，让边界清晰。</h2><p>检查敏感区域、规则与派生结果。</p><el-button text type="primary" @click="router.push('/admin/cases')">选择待复核案例</el-button></div><ProductVisual variant="security"/></article></ScrollReveal><ScrollReveal><article id="publication-story"><p>03 / 教学使用</p><h2>授权、发布与审计。</h2><p>从案例详情进入发布管理，将授权与教学版本关联。</p><el-button text type="primary" @click="router.push('/admin/cases')">查看案例与发布入口</el-button></article></ScrollReveal></section></main></template>
<style scoped>
.admin-product{background:#fff;padding:0 24px 90px}.hero{max-width:1100px;margin:auto;padding:52px 0 56px;text-align:center}.eyebrow{font-size:13px;color:#6e6e73}.hero h1{font-size:clamp(40px,5.1vw,72px);line-height:1.12;letter-spacing:-.045em;margin:18px 0}.summary{color:#6e6e73;font-size:20px;line-height:1.6}.actions{display:flex;justify-content:center;gap:18px;margin:28px 0 44px}.chapters{max-width:1040px;margin:auto}.chapters article{padding:90px 0;border-bottom:1px solid #0000000e;scroll-margin-top:64px}.chapters h2{font-size:clamp(32px,4vw,56px);letter-spacing:-.035em;margin:16px 0}.chapters p{color:#6e6e73;font-size:18px;line-height:1.6}.review .product-visual{margin-top:36px}@media(max-width:600px){.hero{padding-top:38px}.summary{font-size:17px}.chapters article{padding:60px 0}}
.actions :deep(.el-button.is-text),.chapters :deep(.el-button.is-text){background:transparent!important;color:#0071e3}
@media(min-width:701px) and (max-height:800px){
  .hero{padding-top:26px}
  .hero h1{font-size:60px}
  .actions{margin:22px 0 30px}
  .hero :deep(svg){max-height:270px}
}
</style>
