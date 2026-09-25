<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const src = ref<string | null>(null)
const alt = ref('')

function open(img: HTMLImageElement) {
  src.value = img.currentSrc || img.src
  alt.value = img.alt || ''
  document.documentElement.style.overflow = 'hidden'
}

function close() {
  src.value = null
  document.documentElement.style.overflow = ''
}

function onDocClick(e: MouseEvent) {
  const t = e.target as HTMLElement
  if (src.value) return // overlay handles its own clicks
  const img = t.closest?.('.vp-doc img') as HTMLImageElement | null
  if (img && !img.closest('a')) open(img)
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="src" class="lb-overlay" @click="close">
      <img class="lb-img" :src="src" :alt="alt" />
      <div class="lb-hint">点击任意处或按 Esc 关闭</div>
    </div>
  </Teleport>
</template>

<style>
/* doc images get a zoom hint cursor (unscoped so it applies to page content) */
.vp-doc img {
  cursor: zoom-in;
}
</style>

<style scoped>
.lb-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(14, 18, 16, 0.82);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  cursor: zoom-out;
  backdrop-filter: blur(4px);
}
.lb-img {
  max-width: 92vw;
  max-height: 86vh;
  object-fit: contain;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 48px rgba(0, 0, 0, 0.45);
}
.lb-hint {
  color: rgba(232, 240, 235, 0.65);
  font-size: 13px;
  letter-spacing: 0.04em;
}
</style>
