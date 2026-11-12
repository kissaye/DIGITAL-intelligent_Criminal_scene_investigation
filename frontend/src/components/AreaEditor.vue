<script setup lang="ts">
import { ref } from 'vue'
import type { Point3D } from '@/types/viewer'
import type { AreaPayload } from '@/types/area'
defineProps<{ points:Point3D[]; busy?:boolean; error?:string }>()
defineEmits<{save:[value:AreaPayload];cancel:[]}>()
const title=ref(''),description=ref('')
</script>
<template><section class="area-editor"><h3>区域测量 · {{points.length}} 个顶点</h3><p>正式面积与周长以服务端结果为准。</p><el-alert v-if="error" :title="error" type="error" :closable="false"/><el-input v-model="title" :disabled="busy" maxlength="200" placeholder="区域名称"/><el-input v-model="description" :disabled="busy" maxlength="4000" type="textarea" placeholder="区域备注"/><el-button type="primary" :disabled="busy" :loading="busy" @click="$emit('save',{points,title,description,viewerState:{}})">保存区域</el-button><el-button :disabled="busy" @click="$emit('cancel')">取消区域</el-button></section></template>
<style scoped>.area-editor{padding:14px 0;min-width:0}.el-input,.el-textarea{margin:8px 0}</style>
