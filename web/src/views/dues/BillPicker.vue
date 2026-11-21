<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Bill, PrepayOptions } from '@/api/types'
import { periodLabel, rp } from '@/utils/format'

/**
 * Pilih bulan yang dibayar: tagihan yang belum dibayar (v-model = id tagihan)
 * dan bulan mendatang untuk bayar di muka (v-model:periods).
 */
const props = defineProps<{ bills: Bill[]; modelValue: number[]; prepay?: PrepayOptions | null; periods?: string[]; sequential?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [ids: number[]]; 'update:periods': [periods: string[]] }>()

const groups = computed(() => {
  const map = new Map<string, Bill[]>()
  for (const b of props.bills) map.set(b.period, [...(map.get(b.period) ?? []), b])
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
})
const selectedPeriods = computed(() => props.periods ?? [])
const isOn = (items: Bill[]) => items.every((b) => props.modelValue.includes(b.id))

function toggle(items: Bill[]) {
  if (props.sequential) {
    // Wajib berurutan dari tunggakan tertua: centang = ikut semua bulan sebelumnya; batal = ikut semua sesudahnya
    const idx = groups.value.findIndex(([, g]) => g === items)
    const upto = isOn(items) ? idx : idx + 1
    emit('update:modelValue', groups.value.slice(0, upto).flatMap(([, g]) => g.map((b) => b.id)))
    if (isOn(items)) emit('update:periods', [])
    return
  }
  const ids = items.map((b) => b.id)
  emit('update:modelValue', isOn(items) ? props.modelValue.filter((id) => !ids.includes(id)) : [...new Set([...props.modelValue, ...ids])])
}

/** Semua tunggakan sudah dicentang (syarat bayar di muka untuk warga) */
const allArrearsOn = computed(() => groups.value.every(([, g]) => isOn(g)))

function togglePeriod(period: string) {
  if (props.sequential && !allArrearsOn.value) {
    // otomatis ikut melunasi semua tunggakan
    emit('update:modelValue', groups.value.flatMap(([, g]) => g.map((b) => b.id)))
  }
  const list = selectedPeriods.value
  if (list.includes(period)) {
    // bayar di muka harus berurutan: membatalkan satu bulan ikut membatalkan bulan sesudahnya
    emit('update:periods', list.filter((p) => p < period))
  } else {
    const all = props.prepay?.periods ?? []
    emit('update:periods', all.filter((p) => p <= period))
  }
}

const feeNames = computed(() => props.prepay?.fees.map((f) => f.name).join(', ') ?? '')
const showAllFuture = ref(false)
const futureVisible = computed(() => {
  const all = props.prepay?.periods ?? []
  return showAllFuture.value ? all : all.slice(0, Math.max(3, selectedPeriods.value.length + 1))
})

</script>

<template>
  <p v-if="!groups.length && !prepay?.periods.length" class="text-sm text-muted">Tidak ada tagihan yang belum dibayar. 🎉</p>
  <p v-else-if="sequential && groups.length > 1" class="mb-2 text-xs text-muted">Tunggakan dibayar berurutan mulai dari bulan terlama.</p>
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

  <template v-if="prepay?.periods.length">
    <div class="mt-4 mb-2 text-sm font-semibold">Bayar di muka <span class="font-normal text-muted">(tarif saat ini)</span></div>
    <p v-if="sequential && groups.length && !allArrearsOn" class="mb-2 text-xs text-muted">Memilih bulan di muka otomatis ikut melunasi semua tunggakan.</p>
    <div class="grid gap-2 sm:grid-cols-2">
      <label
        v-for="period in futureVisible"
        :key="period"
        class="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed px-3 py-2.5"
        :class="selectedPeriods.includes(period) ? 'border-primary bg-primary-soft' : 'border-line'"
      >
        <input type="checkbox" :checked="selectedPeriods.includes(period)" class="size-4 accent-[var(--c-primary)]" @change="togglePeriod(period)" />
        <span class="flex-1">
          <b>{{ periodLabel(period, true) }}</b>
          <span class="block text-xs text-muted">{{ feeNames }}</span>
        </span>
        <span class="text-sm font-semibold">{{ rp(prepay.monthly_total) }}</span>
      </label>
    </div>
    <button
      v-if="!showAllFuture && futureVisible.length < prepay.periods.length"
      type="button"
      class="mt-2 text-sm text-primary"
      @click="showAllFuture = true"
    >Tampilkan sampai {{ prepay.periods.length }} bulan ke depan</button>
  </template>
</template>
