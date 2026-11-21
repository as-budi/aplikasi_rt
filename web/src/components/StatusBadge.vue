<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string | null | undefined }>()

const MAP: Record<string, [string, string]> = {
  belum_bayar: ['Belum bayar', 'badge-bad'],
  menunggu_verifikasi: ['Menunggu verifikasi', 'badge-warn'],
  lunas: ['Lunas', 'badge-ok'],
  pending: ['Menunggu', 'badge-warn'],
  diterima: ['Diterima', 'badge-ok'],
  disetujui: ['Disetujui', 'badge-ok'],
  ditolak: ['Ditolak', 'badge-bad'],
  dibatalkan: ['Dibatalkan', 'badge-muted'],
}

const info = computed(() => (props.status ? MAP[props.status] : undefined) ?? ['Belum ada tagihan', 'badge-muted'])
</script>

<template>
  <span class="badge" :class="info[1]">{{ info[0] }}</span>
</template>
