<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '@/api/teacher'
import type { GradeItem, Review } from '@/types/teacher'
const route=useRoute(), data=ref<Review>(), items=ref<GradeItem[]>([]), feedback=ref(''), busy=ref(false)
const frozen=computed(()=>data.value?.grade?.status==='PUBLISHED'), total=computed(()=>items.value.reduce((n,i)=>n+Number(i.score||0),0).toFixed(2))
const labels:Record<string,string>={overview:'现场概况',process:'勘验过程',evidenceDescription:'物证描述',preliminaryConclusion:'初步结论'}
async function load(){data.value=await api.review(String(route.params.submissionId));feedback.value=data.value.grade?.feedback||'';items.value=data.value.task.rubric.map(r=>data.value!.grade?.items.find(i=>i.rubricItemId===r.id)||{rubricItemId:r.id!,score:null,comment:''}).map(i=>({...i,score:i.score===null?null:Number(i.score)}))}
async function run(action:()=>Promise<void>){busy.value=true;try{await action()}catch(e){ElMessage.error(api.message(e))}finally{busy.value=false}}
async function save(){await api.saveGrade(String(route.params.submissionId),feedback.value,items.value);ElMessage.success('批改草稿已保存')}
async function publish(){try{await ElMessageBox.confirm('成绩发布后学生可见，且不能继续修改。确认发布？','发布成绩');await run(async()=>{await save();await api.post(`/submissions/${route.params.submissionId}/grade/publish`);await load()})}catch{}}
onMounted(()=>run(load))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>作业批改</h1><el-button @click="$router.push(`/teacher/tasks/${data?.task.id}`)">返回任务</el-button></header><template v-if="data"><h2>{{data.task.title}} · {{data.student.displayName}}（{{data.student.username}}）</h2><el-card><h3>勘验笔录</h3><section v-for="(value,key) in data.submission.reportContent" :key="key"><b>{{labels[key]||key}}</b><pre>{{value}}</pre></section><h3>标记</h3><section v-for="m in data.submission.marks" :key="m.id"><b>{{m.title}}</b><p>{{m.description}}</p><pre>{{JSON.stringify(m.geometry,null,2)}}</pre></section><el-empty v-if="!data.submission.marks.length" description="无标记"/><h3>测距</h3><div v-for="m in data.submission.measurements" :key="m.id"><p>{{m.distance}} m</p><pre>{{m.startPoint}} → {{m.endPoint}}</pre></div></el-card><el-card><h3>评分与反馈 · {{frozen?'已发布':'草稿'}}</h3><el-form :disabled="frozen||busy" label-position="top"><div v-for="(r,index) in data.task.rubric" :key="r.id"><el-form-item :label="`${r.title}（满分 ${r.maxScore}）`"><p>{{r.description}}</p><el-input-number v-model="(items[index].score as number)" :min="0" :max="Number(r.maxScore)" :precision="2" placeholder="未评分"/><el-input v-model="items[index].comment" type="textarea" placeholder="单项反馈"/></el-form-item></div><el-form-item label="总评"><el-input v-model="feedback" type="textarea" :rows="4"/></el-form-item></el-form><p>总分：{{total}}</p><div v-if="!frozen" class="actions"><el-button :disabled="busy" @click="run(save)">保存批改草稿</el-button><el-button type="primary" :disabled="busy" @click="publish">发布成绩</el-button></div></el-card></template></main></template>
