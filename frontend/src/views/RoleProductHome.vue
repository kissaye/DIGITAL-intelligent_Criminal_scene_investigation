<script setup lang="ts">
import { computed } from 'vue'
import BusinessShell from '@/components/BusinessShell.vue'
import ProductVisual from '@/components/ProductVisual.vue'
import ScrollReveal from '@/components/ScrollReveal.vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const teacher = computed(() => route.name === 'teacher')
const chapters = computed(() => teacher.value ? [
  ['组织课程与班级', '在课程下安排教学班级与成员。'],
  ['选择已发布教学版本', '使用经过复核与授权的教学副本。'],
  ['发布任务', '设置班级、实训说明及截止时间。'],
  ['查看提交并反馈', '阅读勘验笔录、标记与测距，并提供评分和评语。'],
] : [
  ['进入受控现场', '打开任务提供的三维场景。'],
  ['标记重点信息', '定位点位、标记区域并记录距离。'],
  ['完成勘验笔录', '记录现场概况、勘验过程、物证描述及初步结论。'],
  ['保存和提交', '编辑时保存草稿，提交后可回看。'],
])
</script>

<template>
  <BusinessShell>
    <main class="role-product">
      <ScrollReveal immediate>
        <section class="hero">
          <p>{{ teacher ? '教师工作台' : '学生工作台' }}</p>
          <h1 v-if="teacher">把真实勘验流程，<br>带进每一次课堂。</h1>
          <h1 v-else>观察现场。记录证据。<br>完成判断。</h1>
          <p>{{ teacher ? '从课程、班级到实训任务，让教学过程与真实现场自然连接。' : '在受控三维现场中完成观察、标记、测量与勘验笔录。' }}</p>
          <div class="actions">
            <RouterLink class="primary" :to="teacher ? '/teacher/tasks?create=1' : '/student/tasks'">{{ teacher ? '创建教学任务' : '进入我的实训' }}</RouterLink>
            <RouterLink v-if="teacher" to="/teacher/courses">管理课程班级</RouterLink>
          </div>
          <figure v-if="teacher" class="teaching-flow" aria-label="教学流程示意">
            <span v-for="stage in ['课程与班级','已发布教学案例','实训任务','学生提交','评分反馈']" :key="stage">{{ stage }}</span>
          </figure>
          <ProductVisual v-else variant="viewer" />
        </section>
      </ScrollReveal>
      <ScrollReveal v-for="([title, description], index) in chapters" :key="title">
        <section class="chapter"><p>0{{ index + 1 }}</p><h2>{{ title }}</h2><p>{{ description }}</p></section>
      </ScrollReveal>
    </main>
  </BusinessShell>
</template>

<style scoped>
.role-product { max-width: 1100px; margin: auto; }
.hero { text-align: center; }
.hero h1 { font-size: clamp(36px, 5.5vw, 72px); line-height: 1.13; letter-spacing: -.045em; margin: 20px 0; }
.hero p, .chapter p { color: #6e6e73; line-height: 1.7; }
.actions { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 22px; margin: 26px 0 38px; }
.actions a { color: #0071e3; text-decoration: none; }
.actions .primary { padding: 12px 19px; border-radius: 12px; background: #0071e3; color: white; }
.teaching-flow { display:flex; align-items:center; justify-content:space-between; gap:14px; margin:0; padding:52px 28px; border-radius:24px; background:#182421; color:#e9f2ee; }
.teaching-flow span { display:flex; align-items:center; gap:14px; font-size:clamp(14px,1.5vw,22px); } .teaching-flow span:not(:last-child)::after { content:'→'; color:#9cbbb0; } @media(max-width:700px){.teaching-flow,.teaching-flow span{flex-direction:column}.teaching-flow span:not(:last-child)::after{content:'↓'}}
.chapter { padding: 50px 0; border-bottom: 1px solid #00000012; }
.chapter h2 { font-size: clamp(28px,4vw,52px); margin: 12px 0; }
</style>
