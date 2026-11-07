<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, type InputInstance } from 'element-plus'
import { createClass, createCourse, getClasses, getCourses, getTeacherStudents, saveClassMembers } from '@/api/teacher'
import type { Course, TeacherStudent, TeachingClass } from '@/types/teacher'

const courses = ref<Course[]>([]), classes = ref<TeachingClass[]>([]), students = ref<TeacherStudent[]>([])
const courseId = ref(''), classId = ref(''), dialog = ref<'course'|'class'|'members'|null>(null)
const first = ref<InputInstance>()
const name = ref(''), description = ref(''), search = ref(''), directorySearch = ref('')
const members = ref<Array<string|number>>([]), busy = ref(false), loading = ref(false)
const activeClass = computed(() => classes.value.find(item => item.id === classId.value))
const matches = (student: TeacherStudent, query: string) => `${student.displayName} ${student.username}`.toLowerCase().includes(query.trim().toLowerCase())
const directory = computed(() => students.value.filter(student => matches(student, directorySearch.value)))
const choices = computed(() => students.value.filter(student => matches(student, search.value)))
function notify(error: unknown) { ElMessage.error(error instanceof Error ? error.message : '操作失败，请重试') }
async function select(id: string, preferredClass = '') {
  courseId.value = id
  classId.value = ''
  classes.value = []
  try {
    const result = await getClasses(id)
    if (courseId.value !== id) return
    classes.value = result
    classId.value = result.find(item => item.id === preferredClass)?.id || result[0]?.id || ''
  } catch (error) { notify(error) }
}
async function load() {
  loading.value = true
  try {
    ;[courses.value, students.value] = await Promise.all([getCourses(), getTeacherStudents()])
    const stored = sessionStorage.getItem('dici.teacher-course')
    const id = courses.value.find(item => item.id === stored)?.id || courses.value[0]?.id
    if (id) await select(id, sessionStorage.getItem('dici.teacher-class') || '')
  } catch (error) { notify(error) } finally { loading.value = false }
}
function chooseClass(id: string) { classId.value = id; sessionStorage.setItem('dici.teacher-class', id) }
async function chooseCourse(id: string) { sessionStorage.setItem('dici.teacher-course', id); await select(id); chooseClass(classId.value) }
function open(kind: 'course'|'class'|'members') {
  name.value = ''; description.value = ''; search.value = ''
  members.value = [...(activeClass.value?.memberIds || [])]
  dialog.value = kind
}
async function save() {
  if (busy.value || !dialog.value) return
  if (dialog.value !== 'members' && !name.value.trim()) { ElMessage.warning('请输入名称'); return }
  busy.value = true
  try {
    if (dialog.value === 'course') {
      const result = await createCourse({ title: name.value.trim(), description: description.value })
      courses.value = await getCourses()
      await chooseCourse(result.id)
    } else if (dialog.value === 'class') {
      const result = await createClass({ courseId: courseId.value, name: name.value.trim() })
      await select(courseId.value, result.id)
      chooseClass(classId.value)
    } else if (activeClass.value) {
      const id = activeClass.value.id
      await saveClassMembers(id, members.value)
      await select(courseId.value, id)
      chooseClass(classId.value)
    }
    dialog.value = null
    ElMessage.closeAll()
    ElMessage.success('已保存')
  } catch (error) { notify(error) } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <main class="courses-page">
    <header><h1>课程与班级</h1><el-button type="primary" @click="open('course')">新建课程</el-button></header>
    <div class="course-layout" v-loading="loading">
      <nav aria-label="课程列表">
        <h2>课程列表</h2>
        <el-empty v-if="!courses.length" description="暂无课程" />
        <button v-for="course in courses" :key="course.id" :aria-current="course.id===courseId" @click="chooseCourse(course.id)">{{ course.title }}</button>
      </nav>
      <section>
        <header><h2>班级与成员</h2><el-button :disabled="!courseId" @click="open('class')">新建班级</el-button></header>
        <el-empty v-if="!classes.length" description="当前课程暂无班级" />
        <div v-else class="class-list">
          <button v-for="item in classes" :key="item.id" :aria-pressed="item.id===classId" @click="chooseClass(item.id)">{{ item.name }} · {{ item.studentCount }} 人</button>
        </div>
        <template v-if="activeClass">
          <header class="directory-head"><div><h3>{{ activeClass.name }}</h3><p>已加入 {{ activeClass.studentCount }} 人</p></div><el-button @click="open('members')">设置成员</el-button></header>
          <el-input v-model="directorySearch" placeholder="搜索学生目录" clearable />
          <ul><li v-for="student in directory" :key="student.id"><span>{{student.displayName}}（{{student.username}}）</span><el-tag :type="activeClass.memberIds.includes(student.id)?'success':'info'">{{activeClass.memberIds.includes(student.id)?'当前班级成员':'未加入'}}</el-tag></li></ul>
          <el-empty v-if="!directory.length" description="没有匹配的学生" />
        </template>
      </section>
    </div>
    <el-dialog :model-value="!!dialog" :title="dialog==='members'?'设置班级成员':dialog==='course'?'新建课程':'新建班级'" width="min(520px, calc(100vw - 28px))" :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy" @update:model-value="(value: boolean)=>{if(!value&&!busy)dialog=null}" @opened="first?.focus()">
      <el-form v-if="dialog!=='members'" @submit.prevent="save">
        <el-input ref="first" v-model="name" :placeholder="dialog==='course'?'课程名称':'班级名称'" />
        <el-input v-if="dialog==='course'" v-model="description" type="textarea" placeholder="课程说明" class="description" />
      </el-form>
      <template v-else>
        <el-input ref="first" v-model="search" placeholder="搜索学生姓名或账号" clearable />
        <p aria-live="polite">已选 {{ members.length }} 人</p>
        <el-checkbox-group v-model="members" class="member-options" :disabled="busy">
          <el-checkbox v-for="student in choices" :key="student.id" :value="student.id">{{ student.displayName }}（{{ student.username }}） · {{activeClass?.memberIds.includes(student.id)?'当前成员':'未加入'}}</el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="!choices.length" description="没有匹配的学生" />
      </template>
      <template #footer><el-button :disabled="busy" @click="dialog=null">取消</el-button><el-button type="primary" :loading="busy" :disabled="busy" @click="save">{{dialog==='members'?'保存成员':'创建'}}</el-button></template>
    </el-dialog>
  </main>
</template>

<style scoped>
header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; }
.course-layout { display:grid; grid-template-columns:minmax(180px,1fr) minmax(0,3fr); margin-top:24px; background:white; border-radius:20px; }
nav,section { padding:24px; min-width:0; }
nav { border-right:1px solid #0001; }
nav button,.class-list button { border:0; border-radius:10px; background:#f5f5f7; color:#1d1d1f; text-align:left; padding:12px; cursor:pointer; }
nav button { display:block; width:100%; margin:6px 0; }
button[aria-current=true],button[aria-pressed=true] { background:#e4effe; color:#0055a8; }
.class-list { display:flex; flex-wrap:wrap; gap:8px; }
.directory-head { margin-top:20px; }
ul { list-style:none; padding:0; }
li { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; padding:12px 0; border-bottom:1px solid #0001; }
.description { margin-top:12px; }
.member-options { display:grid; max-height:45vh; overflow:auto; }
@media(max-width:800px) { .course-layout { grid-template-columns:minmax(0,1fr); } nav { border-right:0; border-bottom:1px solid #0001; } }
</style>
