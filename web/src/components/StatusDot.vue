<script setup lang="ts">
import { computed } from 'vue'
import type { BillStatus } from '@/api/types'

const props = defineProps<{ status: BillStatus | null }>()

const info = computed(() => {
  switch (props.status) {
    case 'lunas':
      return { cls: 'bg-ok-soft text-ok', sym: '✓', label: 'Lunas' }
    case 'menunggu_verifikasi':
      return { cls: 'bg-warn-soft text-warn', sym: '⏳', label: 'Menunggu verifikasi' }
    case 'belum_bayar':
      return { cls: 'bg-bad-soft text-bad', sym: '✕', label: 'Belum bayar' }
    default:
      return { cls: 'text-muted', sym: '·', label: 'Tidak ada tagihan' }
  }
})
</script>

<template>
  <span
    class="inline-grid size-6 place-items-center rounded-[7px] text-xs font-bold"
    :class="info.cls"
    :title="info.label"
    :aria-label="info.label"
  >{{ info.sym }}</span>
</template>
