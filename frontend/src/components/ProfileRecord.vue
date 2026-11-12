<script setup lang="ts">
import type {ProfileRecord} from '@/types/profile'
import {metric} from '@/utils/contracts'
defineProps<{value:ProfileRecord}>()
</script>
<template><section class="profile-record"><b>{{value.title||'未命名剖面'}}</b><p class="length">{{typeof value.pathLength==='number'?metric(value.pathLength)+' m':'模拟剖面 · 待服务端计算'}}</p><p>宽度 {{metric(value.width)}} m · {{value.pointCount??value.points.length}} 个节点</p><p>{{value.description||'—'}}</p><details><summary>节点坐标</summary><p v-for="(point,index) in value.points" :key="index">{{index+1}} · {{point.x}}, {{point.y}}, {{point.z}}</p></details></section></template>
<style scoped>.profile-record{padding:16px 0;border-bottom:1px solid #8884;font-size:12px;overflow-wrap:anywhere}.length{font-size:24px}</style>
