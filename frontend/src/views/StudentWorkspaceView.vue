<script setup lang="ts">
import ProfileEditor from '@/components/ProfileEditor.vue'
import ProfileRecordView from '@/components/ProfileRecord.vue'
import type {ProfilePayload} from '@/types/profile'
import AreaEditor from '@/components/AreaEditor.vue'
import AreaRecord from '@/components/AreaRecord.vue'
import type {AreaPayload} from '@/types/area'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import MeasurementDetails from '@/components/MeasurementDetails.vue'
import MeasurementEditor from '@/components/MeasurementEditor.vue'
import type { MeasurementPayload } from '@/types/viewer'
import PotreeFrame from '@/components/PotreeFrame.vue'
import { getStudentTask, getStudentWorkspace, saveStudentDraft, submitStudentTask } from '@/api/student'
import type { StudentTask, StudentWorkspace } from '@/types/student'
import { measurementResults } from '@/utils/contracts'
import type { Measurement, Point3D } from '@/types/viewer'

const route=useRoute(),router=useRouter(),frame=ref<InstanceType<typeof PotreeFrame>>(),task=ref<StudentTask>(),workspace=ref<StudentWorkspace>(),loading=ref(true),viewerError=ref(''),point=ref<Point3D>({x:0,y:0,z:0}),title=ref(''),description=ref(''),saveState=ref('已保存'),timer=ref<number>(),mock=import.meta.env.VITE_USE_MOCK!=='false'
const taskId=()=>String(route.params.taskId)
const readonly=computed(()=>Boolean(workspace.value?.submitted||task.value?.status==='SUBMITTED'||task.value?.status==='NOT_STARTED'||(task.value?.status==='EXPIRED'&&!task.value.allowLate)))
const pendingMeasurement=ref<Pick<MeasurementPayload,'startPoint'|'endPoint'>>()
const pendingProfile=ref<ProfilePayload>()
function saveProfile(value:ProfilePayload){if(!workspace.value||readonly.value||submitting.value)return;workspace.value.profiles.push({...value,id:crypto.randomUUID()});pendingProfile.value=undefined;frame.value?.profileAction('saved');schedule()}
function removeProfile(id:string){if(!workspace.value||readonly.value||submitting.value)return;workspace.value.profiles=workspace.value.profiles.filter(item=>item.id!==id);schedule()}
const pendingArea=ref<AreaPayload>()
function saveArea(value:AreaPayload){if(!workspace.value||readonly.value||submitting.value)return;workspace.value.areaMeasurements.push({...value,id:crypto.randomUUID()});pendingArea.value=undefined;frame.value?.polygonAction('saved');schedule()}
function removeArea(id:string){if(!workspace.value||readonly.value||submitting.value)return;workspace.value.areaMeasurements=workspace.value.areaMeasurements.filter(item=>item.id!==id);schedule()}
const panelOpen = ref(true)
const submitting = ref(false)
let saving: Promise<boolean> | undefined
let revision = 0
const forcedMasks=computed(()=>workspace.value?.forcedDesensitizationRules.filter(rule=>rule.mode==='HIDE').map(rule=>({id:rule.id,type:'HIDE' as const,title:rule.title,range:{min:[...rule.geometry.min] as [number,number,number],max:[...rule.geometry.max] as [number,number,number]},enforced:true}))||[])
async function load(){loading.value=true;try{const[t,w]=await Promise.all([getStudentTask(taskId()),getStudentWorkspace(taskId())]);task.value=t;workspace.value=w}catch(e){viewerError.value=e instanceof Error?e.message:'实训工作台加载失败'}finally{loading.value=false}}
function schedule(){if(readonly.value||!workspace.value)return;revision++;saveState.value='待保存';if(timer.value)window.clearTimeout(timer.value);timer.value=window.setTimeout(save,900)}
async function save(): Promise<boolean> {
  window.clearTimeout(timer.value)
  if (saving) await saving
  if (!workspace.value || readonly.value) return false
  const revisionAtStart = revision
  const snapshot = JSON.parse(JSON.stringify(workspace.value)) as StudentWorkspace
  saveState.value = '保存中…'
  saving = (async () => {
    try {
      const result = await saveStudentDraft(taskId(), snapshot)
      if (revision === revisionAtStart) { workspace.value = result; saveState.value = '已保存' }
      return true
    } catch (error) {
      saveState.value = '保存失败'
      const status = (error as {response?:{status?:number}}).response?.status
      ElMessage.error(status === 422 ? '笔录或测量格式与接口契约不一致，内容已保留，请检查后重试' : status === 409 ? '任务状态冲突，本地内容已保留，请刷新确认后重试' : '草稿保存失败，本地内容已保留')
      return false
    }
  })()
  try { return await saving } finally { saving = undefined }
}
function addMeasurement(points: MeasurementPayload) {
  if (!workspace.value || readonly.value || submitting.value) return
  const { startPoint: a, endPoint: b } = points
  if (![a.x,a.y,a.z,b.x,b.y,b.z].every(Number.isFinite) || Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)<=1e-6) { ElMessage.warning('起点和终点不能重合'); return }
  workspace.value.measurements.push({ ...points, ...measurementResults(points), id: crypto.randomUUID(), createdAt: new Date().toISOString() })
  pendingMeasurement.value=undefined
  schedule()
}
function removeRecord(kind: 'annotations'|'measurements', id: string) {
  if (!workspace.value || readonly.value || submitting.value) return
  const entries = workspace.value[kind]
  const index = entries.findIndex(item => item.id === id)
  if (index >= 0) { entries.splice(index, 1); schedule() }
}
function addPoint(){if(readonly.value||submitting.value)return;if(!workspace.value||!title.value.trim())return ElMessage.warning('请输入标记标题');workspace.value.annotations.unshift({id:`local-${Date.now()}`,type:'POINT_MARK',geometry:{position:point.value},title:title.value,description:description.value,createdAt:new Date().toISOString()});title.value='';description.value='';schedule()}
async function submit(){if(!workspace.value||readonly.value||submitting.value)return;submitting.value=true;try{if(!await save())return;const value=await submitStudentTask(taskId(),workspace.value);workspace.value.submitted=true;workspace.value.submittedAt=value.submittedAt;workspace.value.submissionVersion=value.version;task.value&&(task.value.status='SUBMITTED');ElMessage.success('实训已提交')}catch(e){ElMessage.error((e as {response?:{status?:number}}).response?.status===409?'当前任务状态不允许提交，请刷新后重试。':(e as {response?:{status?:number}}).response?.status===422?'笔录或测量格式与接口契约不一致，内容已保留':'提交失败')}finally{submitting.value=false}}
onMounted(load)
onBeforeUnmount(()=>window.clearTimeout(timer.value))
</script>
<template><main class="workspace"><header><div><p>学生 / 实训工作台</p><h1>{{task?.name||'实训工作台'}}</h1></div><el-button class="panel-toggle" :aria-expanded="panelOpen" @click="panelOpen=!panelOpen">{{panelOpen?'收起面板':'实训面板'}}</el-button><el-button @click="router.push('/student/tasks')">返回任务</el-button><span class="save-indicator" :class="{failed:saveState==='保存失败'}" role="status">自动保存：{{saveState}}</span></header><el-alert v-if="viewerError" title="无法加载实训工作台" :description="viewerError" type="error" :closable="false" show-icon/><el-skeleton v-else-if="loading" :rows="12" animated/><section v-else-if="workspace" class="layout"><div class="viewer"><PotreeFrame ref="frame" :manifest-url="workspace.manifestUrl" :mock="mock" :masks="forcedMasks" :hide-preview="true" @error="viewerError=$event" @pick="point=$event" @measurement="pendingMeasurement=$event;panelOpen=true" @profile="pendingProfile={...$event,width:1};panelOpen=true" @polygon="pendingArea=$event;panelOpen=true"/></div><p v-if="forcedMasks.length" class="mandatory-warning" role="status">HIDE · 教学强制遮挡已生效，敏感区域不能关闭。</p><aside :hidden="!panelOpen"><MeasurementEditor v-if="pendingMeasurement&&!readonly" :points="pendingMeasurement" :busy="submitting" @save="addMeasurement" @cancel="pendingMeasurement=undefined"/><AreaEditor v-if="pendingArea&&!readonly" :points="pendingArea.points" :busy="submitting" @save="saveArea" @cancel="pendingArea=undefined;frame?.polygonAction('cancel')"/><ProfileEditor v-if="pendingProfile&&!readonly" :points="pendingProfile.points" :busy="submitting" @preview="value=>frame?.profileAction('preview',value as any)" @save="saveProfile" @cancel="pendingProfile=undefined;frame?.profileAction('cancel')"/><el-tabs><el-tab-pane label="实训工具"><el-button-group><el-button :disabled="readonly||submitting" @click="pendingProfile=undefined;frame?.startProfile()">剖面</el-button><el-button :disabled="readonly||submitting" @click="pendingArea=undefined;frame?.startPolygon()">面积测量</el-button><el-button :disabled="readonly||submitting" @click="frame?.startPointPick()">取点</el-button><el-button :disabled="readonly||submitting" @click="frame?.startArea()">重点区域</el-button><el-button :disabled="readonly||submitting" @click="frame?.startMeasurement()">两点测距</el-button><el-button @click="frame?.resetView()">复位</el-button></el-button-group><el-divider>点位标记</el-divider><el-input v-model="title" :disabled="readonly||submitting" placeholder="标记标题"/><el-input v-model="description" :disabled="readonly||submitting" type="textarea" placeholder="描述"/><el-button type="primary" :disabled="readonly||submitting" @click="addPoint">加入草稿</el-button></el-tab-pane><el-tab-pane label="笔录"><el-form label-position="top"><el-form-item label="现场概况"><el-input v-model="workspace.draft.overview" :disabled="readonly||submitting" type="textarea" @input="schedule"/></el-form-item><el-form-item label="勘验过程"><el-input v-model="workspace.draft.process" :disabled="readonly||submitting" type="textarea" @input="schedule"/></el-form-item><el-form-item label="物证描述"><el-input v-model="workspace.draft.evidenceDescription" :disabled="readonly||submitting" type="textarea" @input="schedule"/></el-form-item><el-form-item label="初步结论"><el-input v-model="workspace.draft.preliminaryConclusion" :disabled="readonly||submitting" type="textarea" @input="schedule"/></el-form-item></el-form></el-tab-pane><el-tab-pane label="标记"><el-empty v-if="!workspace.annotations.length" description="暂无标记"/><p v-for="item in workspace.annotations" :key="item.id">{{item.title}} <el-button v-if="!readonly" :disabled="submitting" @click="removeRecord('annotations',item.id)">删除标记</el-button></p></el-tab-pane><el-tab-pane label="测距"><el-empty v-if="!workspace.measurements.length" description="暂无测距"/><p v-for="item in workspace.measurements" :key="item.id"><MeasurementDetails :value="item"/> <el-button v-if="!readonly" :disabled="submitting" @click="removeRecord('measurements',item.id)">删除测距</el-button></p></el-tab-pane><el-tab-pane label="区域"><el-empty v-if="!workspace.areaMeasurements.length" description="暂无区域测量"/><div v-for="item in workspace.areaMeasurements" :key="item.id"><AreaRecord :value="item"/><el-button v-if="!readonly" :disabled="submitting" @click="removeArea(item.id)">删除区域</el-button></div></el-tab-pane><el-tab-pane label="剖面"><el-empty v-if="!workspace.profiles.length" description="暂无剖面"/><div v-for="item in workspace.profiles" :key="item.id"><ProfileRecordView :value="item"/><el-button @click="frame?.profileAction('preview',item as any)">打开剖面</el-button><el-button v-if="!readonly" :disabled="submitting" @click="removeProfile(item.id)">删除剖面</el-button></div></el-tab-pane></el-tabs><footer><p v-if="workspace.submitted">已提交 · 只读回看</p><el-button v-if="!readonly" type="primary" :loading="submitting" :disabled="submitting" @click="submit">提交实训</el-button></footer></aside></section></main></template>
<style scoped>.workspace{height:100vh;background:#f4f7fb}.workspace>header{height:76px;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;background:#fff}.workspace p{margin:0;color:#64748b;font-size:12px}h1{margin:5px 0;font-size:20px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 400px;height:calc(100vh - 76px)}aside{overflow:auto;padding:16px;background:#fff;border-left:1px solid #dde4ee}footer{margin-top:20px}@media(max-width:1100px){.layout{grid-template-columns:1fr}.viewer{height:55vh}}.workspace{position:relative;height:100dvh;min-height:0;overflow:hidden;background:#0b0b0f;color:#f5f5f7}.workspace>header{position:absolute;inset:16px 18px auto;z-index:4;height:auto;min-height:60px;background:#151519ef;color:#f5f5f7;border:1px solid #ffffff24;border-radius:18px;gap:12px;backdrop-filter:blur(14px)}.workspace>header h1{color:inherit}.workspace>header p{color:#b4b4bf}.layout{display:block;height:100%}.viewer{position:absolute;inset:0;height:100%}.layout aside{position:absolute;top:104px;bottom:20px;right:18px;width:min(365px,calc(100vw - 36px));height:auto;border:1px solid #ffffff24;border-radius:20px;background:#18181eef;color:#eee;overflow:auto;padding:22px;backdrop-filter:blur(14px);--el-text-color-primary:#f5f5f7;--el-text-color-regular:#d0d0d8;--el-text-color-secondary:#aaaab6;--el-fill-color-blank:#24242c;--el-border-color:#ffffff2b}.workspace>.el-alert,.workspace>.el-skeleton{position:relative;top:90px;z-index:3}.workspace .panel-toggle{margin-left:auto}.workspace .mandatory-warning{position:absolute;z-index:5;bottom:24px;left:18px;width:max-content;max-width:calc(100vw - 36px);color:#ffd091;background:#302517;border:1px solid #bd8b4e;border-radius:12px;padding:12px}.layout aside[hidden]{display:none}@media(max-width:600px){.layout aside{top:126px;bottom:75px}.workspace>header{flex-wrap:wrap}}.save-indicator{font-size:12px;color:#a9e0c4}.save-indicator.failed{color:#ff9d95}.layout aside :deep(.el-divider__text){background:#18181e;color:#e5e5eb}.layout aside :deep(.el-button:not(.el-button--primary)){background:#292932;color:#f1f1f4;border-color:#555563}.layout aside :deep(.el-button.is-disabled){opacity:.65}.layout aside :deep(.el-tabs__item.is-active){color:#9bc9ff}.layout aside :deep(.el-input__inner),.layout aside :deep(.el-textarea__inner){color:#f5f5f7}.layout aside :deep(.el-textarea.is-disabled .el-textarea__inner),.layout aside :deep(textarea[readonly]),.layout aside :deep(.el-input.is-disabled .el-input__wrapper){background:#292932!important;color:#f3f3f7!important;-webkit-text-fill-color:#f3f3f7;opacity:1}.layout aside :deep(textarea::placeholder){color:#a3a3b1!important;-webkit-text-fill-color:#a3a3b1}.layout aside :deep(.el-tab-pane p){color:#e5e5ed}</style>
