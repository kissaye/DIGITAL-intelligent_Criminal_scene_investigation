/** UI-only demo storage, isolated per mock teacher. Real authorization is server-side. */
import type { Course, Student, TaskForm, TeachingClass, TeachingTask } from '@/types/teacher'

interface State { courses: Course[]; classes: TeachingClass[]; tasks: TeachingTask[] }
const uid = () => crypto.randomUUID()
export async function teacherMock<T>(method: string, path: string, payload: unknown = {}): Promise<T> {
  const key = `dici.mock-teacher-${localStorage.getItem('dici.access-token')}`
  const state: State = JSON.parse(localStorage.getItem(key) || '{"courses":[],"classes":[],"tasks":[]}')
  const [pathname, query] = path.split('?'), parts = pathname.split('/').filter(Boolean)
  const body = payload as Record<string, unknown>
  const course = () => { const item=state.courses.find(c=>c.id===parts[1]);if(!item)throw new Error('课程不存在');return item }
  const group = () => { const item=state.classes.find(c=>c.id===parts[1]);if(!item)throw new Error('班级不存在');return item }
  const task = () => { const item=state.tasks.find(t=>t.id===parts[1]);if(!item)throw new Error('任务不存在');return item }
  let data: unknown
  if(parts[0]==='courses') {
    if(parts.length===1) {
      if(method==='POST'){const c={id:uid(),name:String(body.name),classes:[]};state.courses.push(c);data=c}else data=state.courses
    } else if(parts[2]==='classes') {
      const c=course(), g={id:uid(),courseId:c.id,name:String(body.name),members:[]};state.classes.push(g);c.classes.push({id:g.id,name:g.name});data=g
    } else {const c=course();if(method==='PATCH')c.name=String(body.name);data=c}
  } else if(parts[0]==='classes') {
    const g=group()
    if(parts[2]==='members') {
      if(method==='DELETE')g.members=g.members.filter(s=>s.id!==Number(parts[3]))
      else if(!g.members.some(s=>s.id===Number(body.studentId)))g.members.push({id:Number(body.studentId),username:'student',displayName:'演示学生'})
    } else if(method==='PATCH'){g.name=String(body.name);const c=state.courses.find(c=>c.id===g.courseId)?.classes.find(c=>c.id===g.id);if(c)c.name=g.name}
    data=g
  } else if(parts[0]==='students') {
    const name=new URLSearchParams(query).get('username');data=name==='student'?[{id:1,username:'student',displayName:'演示学生'} satisfies Student]:[]
  } else if(parts[0]==='case-versions') data=[{id:'mock-version-001',teachingTitle:'教学演示案例',versionNumber:1}]
  else if(parts[0]==='tasks') {
    if(parts.length===1){
      if(method==='POST'){const t={...(payload as TaskForm),id:uid(),status:'DRAFT',assignedCount:0,submittedCount:0};t.rubric=t.rubric.map(r=>({...r,id:uid()}));state.tasks.push(t);data=t}
      else {const q=new URLSearchParams(query);data=state.tasks.filter(t=>(!q.get('courseId')||t.courseId===q.get('courseId'))&&(!q.get('status')||t.status===q.get('status')))}
    } else {const t=task()
      if(parts[2]==='submissions')data=[]
      else if(parts[2]==='publish'){if(t.status!=='DRAFT')throw new Error('只有草稿可发布');const members=new Set(t.classIds.flatMap(id=>state.classes.find(c=>c.id===id)?.members.map(s=>s.id)||[]));if(!members.size)throw new Error('请先添加班级学生');t.status='PUBLISHED';t.assignedCount=members.size;data=t}
      else if(parts[2]==='close'){if(t.status!=='PUBLISHED')throw new Error('任务尚未发布');t.status='CLOSED';data=t}
      else {if(method==='PATCH'){if(t.status!=='DRAFT')throw new Error('任务已冻结');Object.assign(t,payload);t.rubric=t.rubric.map(r=>({...r,id:uid()}))}data=t}
    }
  } else throw new Error('模拟模式不提供真实作业批改，请关闭 Mock 后联调')
  localStorage.setItem(key,JSON.stringify(state))
  return structuredClone(data) as T
}
