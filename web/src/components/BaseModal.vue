<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ open: boolean; title?: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-end justify-center bg-black/45 md:items-center md:p-4"
      @click.self="emit('close')"
    >
      <div
        role="dialog"
        aria-modal="true"
        class="max-h-[92dvh] w-full overflow-y-auto rounded-t-2xl bg-surface p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] md:rounded-2xl"
        :class="wide ? 'md:max-w-2xl' : 'md:max-w-lg'"
      >
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">{{ title }}</h2>
          <button class="btn-icon" aria-label="Tutup" @click="emit('close')"><AppIcon name="x" /></button>
        </div>
        <slot />
      </div>
    </div>
  </Teleport>
</template>
