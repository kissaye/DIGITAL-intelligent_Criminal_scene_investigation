<script setup lang="ts">
import type {VolumeMeasurement} from '@/types/volume'
import {metric} from '@/utils/contracts'
defineProps<{value:VolumeMeasurement}>()
</script>
<template><section class="volume-record"><b>{{value.title||'未命名包围盒'}}</b><p class="volume">{{typeof value.volume==='number'?metric(value.volume)+' m³':'模拟包围盒 · 待服务端计算'}}</p><p>长 {{typeof value.length==='number'?metric(value.length):'—'}} · 宽 {{typeof value.width==='number'?metric(value.width):'—'}} · 高 {{typeof value.height==='number'?metric(value.height):'—'}} m</p><p>中心 {{value.center.x}}, {{value.center.y}}, {{value.center.z}}</p><p>旋转 {{metric(value.rotation.x*180/Math.PI)}}, {{metric(value.rotation.y*180/Math.PI)}}, {{metric(value.rotation.z*180/Math.PI)}}°</p><p>{{value.description||'—'}}</p><small>该结果为三维包围盒体积，不代表物体表面重建后的真实体积。</small></section></template>
<style scoped>.volume-record{padding:16px 0;font-size:12px;overflow-wrap:anywhere;border-bottom:1px solid #8884}.volume{font-size:24px}small{color:#e6a23c}</style>
