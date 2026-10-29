<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ manifestUrl: string; mock: boolean }>()
const emit = defineEmits<{
  loaded: []
  error: [message: string]
  camera: [state: Record<string, unknown>]
  pick: [point: { x: number; y: number; z: number }]
  measurement: [points: { startPoint: { x: number; y: number; z: number }; endPoint: { x: number; y: number; z: number } }]
  area: [area: { center: [number, number, number]; size: [number, number, number]; rotation: [number, number, number] }]
}>()
const frame = ref<HTMLIFrameElement>()
const status = ref('正在初始化 Viewer…')
const src = computed(() => `/potree-viewer.html?mock=${props.mock ? '1' : '0'}`)
function send(type: string, payload: Record<string, unknown> = {}) { frame.value?.contentWindow?.postMessage({ source: 'dici-parent', type, ...payload }, window.location.origin) }
function resetView() { send('reset') }
function startPointPick() { send('pick-point') }
function startMeasurement() { send('measure') }
function startArea() { send('area') }
// manifestUrl 由后端受控下发，必须保持为同源的 /api 相对路径；不传递 Token 或原始点云路径。
function load() { if (props.mock) send('load-mock'); else if (props.manifestUrl) send('load', { manifestUrl: props.manifestUrl }); else emit('error', '后端未返回受控点云清单地址，无法加载 Viewer。') }
function message(event: MessageEvent) { if (event.origin !== window.location.origin || event.data?.source !== 'dici-potree') return; if (event.data.type === 'ready') load(); if (event.data.type === 'loaded') { status.value = 'Viewer 已就绪'; emit('loaded') } if (event.data.type === 'error') { status.value = '加载失败'; emit('error', event.data.message || 'Potree 加载失败') } if (event.data.type === 'camera') emit('camera', event.data.camera || {}) ; if (event.data.type === 'pick') emit('pick', event.data.point); if (event.data.type === 'measurement') emit('measurement', event.data); if (event.data.type === 'area') emit('area', event.data.area) }
onMounted(() => { window.addEventListener('message', message); frame.value?.addEventListener('load', load) })
onBeforeUnmount(() => window.removeEventListener('message', message))
watch(() => props.manifestUrl, load)
defineExpose({ resetView, startPointPick, startMeasurement, startArea, status })
</script>
<template><div class="potree-frame"><iframe ref="frame" :src="src" title="Potree 点云浏览器" sandbox="allow-scripts allow-same-origin" /><span class="viewer-status">{{ status }}</span></div></template>
<style scoped>.potree-frame { position: relative; width: 100%; height: 100%; background: #101827; }.potree-frame iframe { width: 100%; height: 100%; border: 0; }.viewer-status { position: absolute; left: 12px; bottom: 10px; padding: 5px 8px; color: #d7e5f6; background: rgb(8 18 32 / 75%); border-radius: 4px; font-size: 12px; }</style>
