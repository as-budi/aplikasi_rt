<script setup lang="ts">
import { computed } from 'vue'
import type { Bill } from '@/api/types'
import { periodLabel, rp } from '@/utils/format'

const props = defineProps<{ bills: Bill[]; modelValue: number[] }>()
const emit = defineEmits<{ 'update:modelValue': [ids: number[]] }>()

// Kelompokkan per bulan: satu centang = semua jenis iuran bulan itu
const groups = computed(() => {
  const map = new Map<string, Bill[]>()
  for (const b of props.bills) map.set(b.period, [...(map.get(b.period) ?? []), b])
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
})

const isOn = (items: Bill[]) => items.every((b) => props.modelValue.includes(b.id))

function toggle(items: Bill[]) {
  const ids = items.map((b) => b.id)
  emit('update:modelValue', isOn(items) ? props.modelValue.filter((id) => !ids.includes(id)) : [...new Set([...props.modelValue, ...ids])])
}
</script>

<template>
  <p v-if="!groups.length" class="text-sm text-muted">Tidak ada tagihan yang belum dibayar. 🎉</p>
  <div class="grid gap-2 sm:grid-cols-2">
    <label
      v-for="[period, items] in groups"
      :key="period"
      class="flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5"
      :class="isOn(items) ? 'border-primary bg-primary-soft' : 'border-line'"
    >
      <input type="checkbox" :checked="isOn(items)" class="size-4 accent-[var(--c-primary)]" @change="toggle(items)" />
      <span class="flex-1">
        <b>{{ periodLabel(period, true) }}</b>
        <span class="block text-xs text-muted">{{ items.map((i) => i.fee_type_name).join(', ') }}</span>
      </span>
      <span class="text-sm font-semibold">{{ rp(items.reduce((s, i) => s + i.amount, 0)) }}</span>
    </label>
  </div>
</template>
