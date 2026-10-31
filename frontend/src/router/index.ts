import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/auth'
import { homeRouteForRoles } from '@/utils/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guestOnly: true } },
  { path: '/admin', name: 'admin', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases', name: 'admin-cases', component: () => import('@/views/CaseListView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/new', name: 'admin-case-new', component: () => import('@/views/CaseCreateView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/:caseId', name: 'admin-case-detail', component: () => import('@/views/CaseDetailView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/:caseId/viewer', name: 'admin-case-viewer', component: () => import('@/views/CaseViewerView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/teacher/courses', name: 'teacher-courses', component: () => import('@/views/TeacherCoursesView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/courses/:courseId', name: 'teacher-course', component: () => import('@/views/TeacherCoursesView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks', name: 'teacher-tasks', component: () => import('@/views/TeacherTasksView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks/new', name: 'teacher-task-new', component: () => import('@/views/TeacherTaskDetailView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks/:taskId', name: 'teacher-task', component: () => import('@/views/TeacherTaskDetailView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/submissions/:submissionId', name: 'teacher-review', component: () => import('@/views/TeacherSubmissionView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/student/submissions/:submissionId', name: 'student-submission', component: () => import('@/views/StudentSubmissionView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/teacher', name: 'teacher', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/student', name: 'student', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/student/tasks', name: 'student-tasks', component: () => import('@/views/StudentTaskListView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/student/tasks/:taskId', name: 'student-task-workspace', component: () => import('@/views/StudentWorkspaceView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore()
  if (to.meta.guestOnly && auth.isAuthenticated) return homeRouteForRoles(auth.user?.roles)
  if (!to.meta.requiresAuth) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  const roles = (to.meta.roles as string[] | undefined) || []
  if (!roles.some((role) => auth.user?.roles.includes(role as UserRole))) return homeRouteForRoles(auth.user?.roles)
  return true
})

export default router
