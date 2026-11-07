<script setup lang="ts">
import BusinessShell from '@/components/BusinessShell.vue'
</script>

<template>
  <router-view v-if="!$route.meta.requiresAuth || $route.meta.fullscreen || $route.meta.productPage" />
  <BusinessShell v-else><router-view /></BusinessShell>
</template>
