<script setup lang="ts">
import { ref } from 'vue'
import type { MeasurementPayload } from '@/types/viewer'
defineProps<{ points: Pick<MeasurementPayload,'startPoint'|'endPoint'>; busy?: boolean }>()
defineEmits<{ save: [value: MeasurementPayload]; cancel: [] }>()
const title = ref(''), description = ref('')
</script>
<template><section class="measurement-editor"><h3>测量结果</h3><p>两点已选取，请填写名称与备注后保存。</p><el-input v-model="title" :disabled="busy" placeholder="测量名称"/><el-input v-model="description" :disabled="busy" type="textarea" placeholder="测量备注"/><el-button type="primary" :loading="busy" :disabled="busy" @click="$emit('save',{...points,title,description,viewerState:{}})">保存测量</el-button><el-button :disabled="busy" @click="$emit('cancel')">取消</el-button></section></template>
<style scoped>.measurement-editor{padding:16px 0;border-bottom:1px solid #8884}.el-input,.el-textarea{margin:8px 0}.measurement-editor p{font-size:12px}</style>
