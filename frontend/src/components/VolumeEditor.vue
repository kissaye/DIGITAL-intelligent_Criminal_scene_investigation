<script setup lang="ts">
import {ref} from 'vue'
import type {VolumePayload} from '@/types/volume'
defineProps<{value:VolumePayload;busy?:boolean;error?:string}>()
defineEmits<{save:[value:VolumePayload];cancel:[]}>()
const title=ref(''),description=ref('')
</script>
<template><section><h3>包围盒 · 待服务端计算</h3><p>该结果为三维包围盒体积，不代表物体表面重建后的真实体积。</p><el-alert v-if="error" :title="error" type="error" :closable="false"/><el-input v-model="title" placeholder="包围盒名称" maxlength="200" :disabled="busy"/><el-input v-model="description" type="textarea" placeholder="包围盒备注" maxlength="4000" :disabled="busy"/><div><el-button type="primary" :disabled="busy" :loading="busy" @click="$emit('save',{...value,title,description,viewerState:{}})">保存包围盒</el-button><el-button :disabled="busy" @click="$emit('cancel')">取消包围盒</el-button></div></section></template>
<style scoped>section{min-width:0;padding:16px 0}p{font-size:12px}.el-input,.el-textarea{margin:8px 0}section>div:last-child{display:flex;flex-wrap:wrap;gap:8px}</style>
