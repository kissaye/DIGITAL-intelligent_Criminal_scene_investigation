<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
const props = withDefaults(defineProps<{ delay?: number; immediate?: boolean }>(), { delay: 0, immediate: false })
const element = ref<HTMLElement>()
const visible = ref(true)
let observer: IntersectionObserver | undefined
onMounted(() => {
  if (props.immediate || matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return
  visible.value = false
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) { visible.value = true; observer?.disconnect() }
  }, { threshold: 0.08 })
  if (element.value) observer.observe(element.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
<template><div ref="element" class="scroll-reveal" :class="{ visible }" :style="{ '--reveal-delay': `${Math.min(Math.max(delay,0),300)}ms` }"><slot/></div></template>
<style scoped>
.scroll-reveal { opacity: 0; transform: translateY(18px); transition: opacity 360ms ease var(--reveal-delay), transform 360ms ease var(--reveal-delay); }
.scroll-reveal.visible { opacity: 1; transform: none; }
@media(prefers-reduced-motion:reduce) { .scroll-reveal { opacity:1; transform:none; transition:none; } }
</style>
