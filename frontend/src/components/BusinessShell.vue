<script setup lang="ts">
import { useRouter } from 'vue-router'
import GlobalNav from './GlobalNav.vue'
const router=useRouter()
</script>
<template><div class="business-shell"><GlobalNav signed-in @section="router.push('/admin#publication-story')"/><div class="business-content"><slot/></div></div></template>
<style scoped>.business-shell{min-height:100vh;background:#f5f5f7}.business-content{max-width:1440px;margin:auto;padding:60px 48px 80px;min-width:0}@media(max-width:700px){.business-content{padding:38px 20px 64px}}</style>
