<script setup lang="ts">
import type { AreaMeasurement } from '@/types/area'
import { metric } from '@/utils/contracts'
defineProps<{ value: AreaMeasurement }>()
</script>
<template><section class="area-record"><b>{{value.title||'未命名区域'}}</b><p class="area">{{typeof value.area==='number'?metric(value.area)+' m²':'模拟区域 · 等待服务端计算'}}</p><p>{{value.description||'—'}}</p><p>闭合周长 {{typeof value.perimeter==='number'?metric(value.perimeter)+' m':'—'}} · 顶点 {{value.pointCount??value.points.length}}</p><p>最大平面偏差 {{typeof value.maxPlaneDeviation==='number'?metric(value.maxPlaneDeviation)+' m':'—'}}</p><details><summary>顶点坐标</summary><p v-for="(point,i) in value.points" :key="i">{{i+1}} · {{point.x}}, {{point.y}}, {{point.z}}</p></details></section></template>
<style scoped>.area-record{padding:16px 0;border-bottom:1px solid #8884;overflow-wrap:anywhere;font-size:12px}.area{font-size:24px;margin:8px 0}</style>
