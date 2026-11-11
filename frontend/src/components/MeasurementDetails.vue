<script setup lang="ts">
import { computed } from 'vue'
import type { MeasurementPayload, Measurement } from '@/types/viewer'
import { measurementResults, metric } from '@/utils/contracts'
const props = defineProps<{ value: MeasurementPayload & Partial<Measurement> }>()
const result = computed(() => measurementResults(props.value))
</script>
<template>
  <div class="measurement-details">
    <strong>{{value.title || '未命名测量'}}</strong>
    <p class="distance">{{result.distance > 1e-6 ? metric(result.distance) + ' m' : '无效测距'}}</p>
    <p>{{value.description || '—'}}</p>
    <p>水平距离 {{metric(result.horizontalDistance)}} m · 垂直高度 {{metric(result.verticalDistance)}} m</p>
    <details><summary>坐标分量</summary><p>ΔX {{metric(result.deltaX)}} m · ΔY {{metric(result.deltaY)}} m · ΔZ {{metric(result.deltaZ)}} m</p><p>起点 {{value.startPoint?.x}}, {{value.startPoint?.y}}, {{value.startPoint?.z}}</p><p>终点 {{value.endPoint?.x}}, {{value.endPoint?.y}}, {{value.endPoint?.z}}</p></details>
  </div>
</template>
<style scoped>.measurement-details{min-width:0;overflow-wrap:anywhere;font-size:12px;line-height:1.7}.distance{font-size:24px;margin:8px 0}.measurement-details p{color:inherit}summary{cursor:pointer}</style>
