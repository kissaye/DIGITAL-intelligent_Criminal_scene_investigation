<script setup lang="ts">
import { ref } from 'vue'
import type { Point3D } from '@/types/viewer'
import type { ProfilePayload } from '@/types/profile'
defineProps<{ points:Point3D[]; busy?:boolean; error?:string }>()
defineEmits<{save:[value:ProfilePayload];preview:[value:ProfilePayload];cancel:[]}>()
const width=ref(1),title=ref(''),description=ref('')
</script>
<template><section class="profile-editor"><h3>剖面 · {{points.length}} 个节点</h3><el-alert v-if="error" :title="error" type="error" :closable="false"/><label>剖面宽度（米）</label><el-input-number v-model="width" :min=".01" :max="100" :precision="2" :disabled="busy"/><el-input v-model="title" maxlength="200" placeholder="剖面名称" :disabled="busy"/><el-input v-model="description" maxlength="4000" type="textarea" placeholder="剖面备注" :disabled="busy"/><div><el-button :disabled="busy" @click="$emit('preview',{points,width,title,description,viewerState:{}})">预览剖面</el-button><el-button type="primary" :disabled="busy" :loading="busy" @click="$emit('save',{points,width,title,description,viewerState:{}})">保存剖面</el-button><el-button :disabled="busy" @click="$emit('cancel')">取消</el-button></div></section></template>
<style scoped>.profile-editor{padding:16px 0;min-width:0}.el-input,.el-textarea{margin:8px 0}.profile-editor>div:last-child{display:flex;flex-wrap:wrap;gap:8px}.profile-editor label{display:block;font-size:12px;margin-bottom:8px}</style>
