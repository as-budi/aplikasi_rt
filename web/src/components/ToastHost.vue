<script setup lang="ts">
import { useToast } from '@/stores/toast'

const toast = useToast()
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-24 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-8" aria-live="polite">
    <div
      v-for="t in toast.items"
      :key="t.id"
      class="max-w-md rounded-xl px-4 py-2.5 text-sm shadow-lg"
      :class="t.kind === 'error' ? 'bg-bad text-white' : 'bg-ink text-bg'"
    >
      {{ t.text }}
    </div>
  </div>
</template>
