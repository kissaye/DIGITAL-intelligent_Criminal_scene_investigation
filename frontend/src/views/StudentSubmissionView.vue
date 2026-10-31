<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http, { responseData } from '@/api/http'
import { getSubmittedWork } from '@/api/student'
import { message } from '@/api/teacher'
import type { Grade } from '@/types/teacher'
import type { DraftResponse } from '@/types/student'
const route=useRoute(), submission=ref<DraftResponse>(), grade=ref<Grade>(), error=ref(''), notice=ref(''), busy=ref(false)
const labels:Record<string,string>={overview:'现场概况',process:'勘验过程',evidenceDescription:'物证描述',preliminaryConclusion:'初步结论'}
onMounted(async()=>{busy.value=true;const path=`/api/v1/student/submissions/${route.params.submissionId}`;try{submission.value=await getSubmittedWork(String(route.params.submissionId));if(import.meta.env.VITE_USE_MOCK!=='false'){notice.value='模拟模式不包含教师真实评分';return}try{grade.value=responseData<Grade>(await http.get(`${path}/grade`))}catch(e){notice.value=(e as {response?:{status:number}}).response?.status===404?'教师尚未发布成绩':message(e)}}catch(e){error.value=message(e)}finally{busy.value=false}})
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>我的提交与成绩</h1><el-button @click="$router.push('/student/tasks')">返回任务</el-button></header><el-alert v-if="error" :title="error" type="error"/><el-card v-if="submission"><h2>勘验笔录</h2><section v-for="(value,key) in submission.reportContent" :key="key"><b>{{labels[key]||key}}</b><pre>{{value}}</pre></section><h3>标记</h3><div v-for="m in submission.marks" :key="m.id"><b>{{m.title}}</b><p>{{m.description}}</p><pre>{{m.geometry}}</pre></div><h3>测距</h3><pre v-for="m in submission.measurements" :key="m.id">{{m.startPoint}} → {{m.endPoint}}</pre></el-card><el-alert v-if="notice" :title="notice" type="info" :closable="false"/><el-card v-if="grade"><h2>成绩：{{grade.totalScore}}</h2><p>{{grade.feedback||'无总评'}}</p><div v-for="r in grade.rubric" :key="r.id"><h3>{{r.title}} · {{grade.items.find(i=>i.rubricItemId===r.id)?.score}} / {{r.maxScore}}</h3><p>{{grade.items.find(i=>i.rubricItemId===r.id)?.comment||'无单项反馈'}}</p></div></el-card></main></template>
