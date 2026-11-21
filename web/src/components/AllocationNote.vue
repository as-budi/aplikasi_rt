<script setup lang="ts">
import { computed } from 'vue'
import { periodLabel, rp } from '@/utils/format'
import { previewAllocation, type AllocItem } from '@/utils/allocation'

/** Penjelasan apa yang terjadi dengan nominal yang dibayar: pas, lebih (titipan/dikembalikan), atau kurang. */
const props = defineProps<{ items: AllocItem[]; received: number; credit: number; refund?: boolean; who?: 'warga' | 'pengurus' }>()

const p = computed(() => previewAllocation(props.items, props.received || 0, props.credit))
const months = (list: string[]) => list.map((x) => periodLabel(x)).join(', ')
const state = computed(() => {
  if (!props.items.length) return null
  if (p.value.unpaid.length) return 'kurang'
  return p.value.leftover > 0 ? 'lebih' : 'pas'
})
</script>

<template>
  <div
    v-if="state"
    class="mb-4 rounded-xl px-3 py-2.5 text-sm"
    :class="{ 'bg-ok-soft text-ok': state === 'pas', 'bg-primary-soft text-primary': state === 'lebih', 'bg-warn-soft text-warn': state === 'kurang' }"
    role="status"
  >
    <p class="mb-1 font-semibold">
      Tagihan dipilih {{ rp(p.total) }} · dibayar {{ rp(received || 0) }}<template v-if="credit"> + titipan {{ rp(credit) }}</template>
    </p>
    <template v-if="state === 'pas'">Pas. {{ months(p.paid) }} akan lunas.</template>
    <template v-else-if="state === 'lebih'">
      {{ months(p.paid) }} akan lunas.
      <template v-if="refund && p.refundable">
        Kelebihan {{ rp(p.refundable) }} <b>dikembalikan ke warga</b> dan dicatat sebagai pengeluaran kas<template v-if="p.leftover - p.refundable">; sisa titipan {{ rp(p.leftover - p.refundable) }}</template>.
      </template>
      <template v-else>
        Sisa {{ rp(p.leftover) }} <b>disimpan sebagai saldo titipan</b> dan otomatis dipakai untuk tagihan berikutnya.
      </template>
    </template>
    <template v-else>
      <b>Kurang {{ rp(p.shortfall) }}.</b>{{ ' ' }}
      <template v-if="p.paid.length">{{ months(p.paid) }} akan lunas; </template>
      {{ months(p.unpaid) }} belum lunas.
      <template v-if="p.leftover">Uang {{ rp(p.leftover) }} disimpan sebagai titipan sampai cukup.</template>
      <template v-if="who === 'warga'"> Anda bisa menambah transfer, atau memilih lebih sedikit bulan.</template>
    </template>
  </div>
</template>
