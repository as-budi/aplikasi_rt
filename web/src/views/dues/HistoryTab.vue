<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { Bill, BillStatus, Payment, PrepayOptions } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import { currentYear, dateLabel, periodLabel, rp } from '@/utils/format'
import { METHOD } from '@/utils/labels'
import BaseModal from '@/components/BaseModal.vue'
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
const credit = ref(0)
const payments = ref<Payment[]>([])
const toast = useToast()
const cancelling = ref<Payment | null>(null)
const reason = ref('')
const busy = ref(false)

async function cancelPayment() {
  if (!cancelling.value) return
  if (!reason.value.trim()) return toast.error('Tuliskan alasan pembatalan.')
  busy.value = true
  try {
    await http.post(`/payments/${cancelling.value.id}/cancel/`, { reason: reason.value })
    toast.ok('Pembayaran dibatalkan; tagihan kembali belum bayar')
    cancelling.value = null
    reason.value = ''
    load()
  } catch (e) {
    toast.error(errMsg(e))
  } finally {
    busy.value = false
  }
}
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
    const [b, o, p] = await Promise.all([
      fetchAll<Bill>('/bills/', { household: target.value, year: year.value }),
      http.get<PrepayOptions>('/bills/prepay-options/', { params: { household: target.value } }),
      fetchAll<Payment>('/payments/', { household: target.value, year: year.value }),
    ])
    bills.value = b
    credit.value = o.data.credit
    payments.value = p
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
    <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3">
      <div class="card"><div class="text-sm text-muted">Dibayar {{ year }}</div><div class="text-xl font-bold">{{ rp(paid) }}</div></div>
      <div class="card">
        <div class="text-sm text-muted">Belum dibayar</div>
        <div class="text-xl font-bold" :class="{ 'text-bad': unpaid > 0 }">{{ rp(unpaid) }}</div>
      </div>
      <div class="card col-span-2 md:col-span-1">
        <div class="text-sm text-muted">Saldo titipan</div>
        <div class="text-xl font-bold" :class="{ 'text-primary': credit > 0 }">{{ rp(credit) }}</div>
        <div class="text-xs text-muted">otomatis dipakai untuk tagihan berikutnya</div>
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

    <div class="card mt-4">
      <h2 class="card-title">Pembayaran {{ year }}</h2>
      <p v-if="!payments.length" class="text-sm text-muted">Belum ada pembayaran.</p>
      <div class="list">
        <div v-for="p in payments" :key="p.id" class="flex flex-wrap items-center gap-3 py-3" :class="{ 'opacity-60': p.cancelled_at }">
          <div class="min-w-0 flex-1">
            <b :class="{ 'line-through': p.cancelled_at }">{{ p.method === 'titipan' ? 'Dari saldo titipan' : rp(p.total) }}</b>
            <span class="text-sm text-muted"> · {{ dateLabel(p.paid_at) }} · {{ p.method_label }}</span>
            <div class="text-sm text-muted">
              {{ p.periods_label ? `Melunasi ${p.periods_label}` : 'Disimpan sebagai titipan' }}
              <template v-if="p.credit_change > 0"> · +{{ rp(p.credit_change) }} titipan</template>
              <template v-else-if="p.credit_change < 0"> · pakai titipan {{ rp(-p.credit_change) }}</template>
              <template v-if="p.refund"> · dikembalikan {{ rp(p.refund) }}</template>
            </div>
            <div v-if="p.cancelled_at" class="text-xs text-bad">Dibatalkan {{ dateLabel(p.cancelled_at) }} oleh {{ p.cancelled_by_name }}: {{ p.cancel_reason }}</div>
          </div>
          <span v-if="p.cancelled_at" class="badge badge-muted">Dibatalkan</span>
          <button
            v-else-if="auth.isStaff && p.method !== 'titipan'"
            class="btn btn-sm btn-danger"
            @click="cancelling = p; reason = ''"
          >Batalkan</button>
        </div>
      </div>
    </div>
  </LoadState>

  <BaseModal :open="!!cancelling" title="Batalkan pembayaran" @close="cancelling = null">
    <template v-if="cancelling">
      <p class="mb-3 text-sm">
        Pembayaran <b>{{ rp(cancelling.total) }}</b> tanggal {{ dateLabel(cancelling.paid_at) }}
        <template v-if="cancelling.periods_label">untuk <b>{{ cancelling.periods_label }}</b></template> akan dibatalkan.
      </p>
      <ul class="mb-4 list-disc space-y-1 pl-5 text-sm text-muted">
        <li>Bulan tersebut kembali <b>belum bayar</b>; tagihan bulan mendatang (bayar di muka) dihapus.</li>
        <li>Uangnya tidak lagi dihitung di Kas RT<template v-if="cancelling.refund">, dan catatan pengembalian {{ rp(cancelling.refund) }} ikut dihapus</template>.</li>
        <li v-if="cancelling.credit_change">Saldo titipan disesuaikan kembali.</li>
        <li>Pembayaran tetap tercatat sebagai <b>dibatalkan</b> beserta alasannya (tidak dihapus).</li>
      </ul>
      <label class="field"><span>Alasan pembatalan *</span><input v-model="reason" class="input" required placeholder="mis. uang tidak masuk ke rekening RT" /></label>
      <button class="btn btn-primary w-full" :disabled="busy" @click="cancelPayment">Batalkan pembayaran</button>
    </template>
  </BaseModal>
</template>
