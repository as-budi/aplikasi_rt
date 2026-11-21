<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errMsg, fetchAll } from '@/api/http'
import type { Bill, BillStatus } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { currentYear, dateLabel, periodLabel, rp } from '@/utils/format'
import { METHOD } from '@/utils/labels'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import StatusDot from '@/components/StatusDot.vue'
import HouseholdPicker from './HouseholdPicker.vue'

const props = defineProps<{ householdId: number | null }>()
const emit = defineEmits<{ change: [id: number] }>()
const auth = useAuthStore()

const year = ref(currentYear())
const years = [currentYear(), currentYear() - 1, currentYear() - 2]
const bills = ref<Bill[]>([])
const loading = ref(false)
const error = ref('')

// Pengurus memilih KK; warga selalu KK sendiri
const target = computed(() => (auth.isStaff ? props.householdId ?? auth.user?.household_id ?? null : auth.user?.household_id ?? null))

const groups = computed(() => {
  const map = new Map<string, Bill[]>()
  for (const b of bills.value) map.set(b.period, [...(map.get(b.period) ?? []), b])
  return [...map.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([period, items]) => {
      const statuses = new Set(items.map((i) => i.status))
      const status: BillStatus = statuses.size === 1 && statuses.has('lunas') ? 'lunas' : statuses.has('menunggu_verifikasi') ? 'menunggu_verifikasi' : 'belum_bayar'
      return { period, items, status, total: items.reduce((s, i) => s + i.amount, 0), paidAt: items.find((i) => i.paid_at)?.paid_at ?? null, method: items.find((i) => i.method)?.method ?? null }
    })
})
const paid = computed(() => bills.value.filter((b) => b.status === 'lunas').reduce((s, b) => s + b.amount, 0))
const unpaid = computed(() => bills.value.filter((b) => b.status === 'belum_bayar').reduce((s, b) => s + b.amount, 0))
const label = computed(() => bills.value[0]?.household_label ?? '')

async function load() {
  if (!target.value) return
  loading.value = true
  error.value = ''
  try {
    bills.value = await fetchAll<Bill>('/bills/', { household: target.value, year: year.value })
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

watch([target, year], load, { immediate: true })
</script>

<template>
  <div class="mb-4 grid gap-2 md:grid-cols-[1fr_auto]">
    <HouseholdPicker v-if="auth.isStaff" :model-value="target" @update:model-value="(id) => emit('change', id)" />
    <select v-model="year" class="input md:w-32"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select>
  </div>

  <p v-if="!target" class="card text-muted">
    {{ auth.isStaff ? 'Pilih KK untuk melihat riwayat iurannya.' : 'Akun Anda belum terhubung ke data warga. Hubungi pengurus RT.' }}
  </p>
  <LoadState v-else :loading="loading" :error="error" :empty="!bills.length" :empty-text="`Belum ada tagihan pada ${year}.`" @retry="load">
    <div class="mb-4 grid grid-cols-2 gap-3">
      <div class="card"><div class="text-sm text-muted">Dibayar {{ year }}</div><div class="text-xl font-bold">{{ rp(paid) }}</div></div>
      <div class="card">
        <div class="text-sm text-muted">Belum dibayar</div>
        <div class="text-xl font-bold" :class="{ 'text-bad': unpaid > 0 }">{{ rp(unpaid) }}</div>
      </div>
    </div>
    <div class="card">
      <div class="mb-1 flex items-center justify-between gap-2">
        <h2 class="text-[15px] font-semibold">Riwayat {{ label && `rumah ${label}` }}</h2>
        <RouterLink v-if="!auth.isStaff && unpaid" to="/iuran?tab=unggah" class="btn btn-sm btn-primary">Unggah bukti</RouterLink>
      </div>
      <div class="list">
        <div v-for="g in groups" :key="g.period" class="flex items-center gap-3 py-3">
          <StatusDot :status="g.status" />
          <div class="min-w-0 flex-1">
            <b>{{ periodLabel(g.period, true) }}</b>
            <div class="text-sm text-muted">
              {{ rp(g.total) }} · {{ g.items.map((i) => i.fee_type_name).join(', ') }}
              <template v-if="g.paidAt"> · dibayar {{ dateLabel(g.paidAt) }} ({{ METHOD[g.method ?? ''] ?? '' }})</template>
            </div>
          </div>
          <StatusBadge :status="g.status" class="hidden sm:inline-flex" />
        </div>
      </div>
    </div>
  </LoadState>
</template>
