<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import * as api from '@/api/teacher'
import type { Course, Student, TeachingClass } from '@/types/teacher'

const route=useRoute()
const list = ref<Course[]>([]), selected = ref<Course>(), group = ref<TeachingClass>(), search = ref(''), found = ref<Student[]>([]), busy = ref(false)
async function run(action: () => Promise<void>) { busy.value = true; try { await action() } catch (e) { ElMessage.error(api.message(e)) } finally { busy.value = false } }
async function load() { list.value = await api.courses(); if (selected.value) selected.value = list.value.find(c => c.id === selected.value?.id) }
async function name(title: string, value = '') { const p = await ElMessageBox.prompt('名称', title, { inputValue: value, inputValidator: v => Boolean(v?.trim()) && v.trim().length <= 200 || '请输入 1–200 字名称' }); return p.value.trim() }
async function createCourse() { try { const value = await name('创建课程'); await run(async () => { await api.post('/courses', { name: value }); await load() }) } catch {} }
async function renameCourse(c: Course) { try { const value = await name('编辑课程', c.name); await run(async () => { await api.patch(`/courses/${c.id}`, { name: value }); await load() }) } catch {} }
async function createClass() { if (!selected.value) return; try { const value = await name('创建班级'); await run(async () => { await api.post(`/courses/${selected.value!.id}/classes`, { name: value }); await load() }) } catch {} }
async function renameClass() { if (!group.value) return; try { const value = await name('编辑班级', group.value.name); await run(async () => { await api.patch(`/classes/${group.value!.id}`, { name: value }); group.value = await api.teachingClass(group.value!.id); await load() }) } catch {} }
function select(c: Course) { selected.value = c; group.value = undefined; found.value = [] }
function openClass(id: string) { run(async () => { group.value = await api.teachingClass(id); found.value = [] }) }
function add(s: Student) { run(async () => { group.value = await api.post<TeachingClass>(`/classes/${group.value!.id}/members`, { studentId: s.id }) }) }
function remove(s: Student) { run(async () => { await api.removeMember(group.value!.id, s.id); group.value = await api.teachingClass(group.value!.id) }) }
onMounted(() => run(async()=>{await load();const c=list.value.find(c=>c.id===route.params.courseId);if(c)select(c)}))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>课程与班级</h1><el-button @click="$router.push('/teacher/tasks')">教学任务</el-button><el-button @click="$router.push('/teacher')">首页</el-button></header><el-button type="primary" @click="createCourse">创建课程</el-button><el-table :data="list"><el-table-column prop="name" label="课程"/><el-table-column label="操作"><template #default="{row}"><el-button link @click="select(row)">管理班级</el-button><el-button link @click="renameCourse(row)">编辑</el-button></template></el-table-column></el-table><el-card v-if="selected"><h2>{{ selected.name }}</h2><el-button @click="createClass">创建班级</el-button><el-button v-for="c in selected.classes" :key="c.id" @click="openClass(c.id)">{{c.name}}</el-button><section v-if="group"><h3>{{group.name}} <el-button link @click="renameClass">编辑名称</el-button></h3><p>班级成员变动不会改变已发布任务的学生名单。</p><el-input v-model="search" placeholder="输入完整学生用户名" style="max-width:300px"/><el-button @click="run(async()=>{found=await api.findStudent(search)})">查找学生</el-button><div v-for="s in found" :key="s.id">{{s.displayName}}（{{s.username}}）<el-button link @click="add(s)">加入班级</el-button></div><el-table :data="group.members"><el-table-column prop="username" label="用户名"/><el-table-column prop="displayName" label="姓名"/><el-table-column label="操作"><template #default="{row}"><el-button link type="danger" @click="remove(row)">移除</el-button></template></el-table-column></el-table></section></el-card></main></template>
