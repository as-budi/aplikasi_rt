<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { Bill, PayMethod, PrepayOptions } from '@/api/types'
import { useToast } from '@/stores/toast'
import { previewAllocation, selectedItems } from '@/utils/allocation'
import { rp, todayISO } from '@/utils/format'
import AllocationNote from '@/components/AllocationNote.vue'
import BillPicker from './BillPicker.vue'
import HouseholdPicker from './HouseholdPicker.vue'

const props = defineProps<{ householdId: number | null }>()
const emit = defineEmits<{ change: [id: number] }>()
const toast = useToast()

const bills = ref<Bill[]>([])
const prepay = ref<PrepayOptions | null>(null)
const pendingCount = ref(0)
const selected = ref<number[]>([])
const periods = ref<string[]>([])
const form = reactive<{ method: PayMethod; paid_at: string; note: string; amount: number; refund: boolean }>({
  method: 'tunai', paid_at: todayISO(), note: '', amount: 0, refund: false,
})
const amountTouched = ref(false)
const busy = ref(false)
const error = ref('')

const credit = computed(() => prepay.value?.credit ?? 0)
const items = computed(() => selectedItems(bills.value, selected.value, periods.value, prepay.value?.monthly_total ?? 0))
const total = computed(() => items.value.reduce((s, i) => s + i.amount, 0))
const alloc = computed(() => previewAllocation(items.value, form.amount, credit.value))
watch(total, (t) => {
  if (!amountTouched.value) form.amount = Math.max(0, t - credit.value)
})

async function load() {
  selected.value = []
  periods.value = []
  bills.value = []
  amountTouched.value = false
  form.refund = false
  if (!props.householdId) return
  const [all, opts] = await Promise.all([
    fetchAll<Bill>('/bills/', { household: props.householdId }),
    http.get<PrepayOptions>('/bills/prepay-options/', { params: { household: props.householdId } }),
  ])
  bills.value = all.filter((b) => b.status === 'belum_bayar')
  pendingCount.value = all.filter((b) => b.status === 'menunggu_verifikasi').length
  prepay.value = opts.data
}

async function submit() {
  if (!props.householdId || !items.value.length) return
  busy.value = true
  error.value = ''
  try {
    await http.post('/payments/', {
      household: props.householdId, bills: selected.value, periods: periods.value,
      method: form.method, paid_at: form.paid_at, note: form.note, amount: form.amount,
      refund_excess: form.refund && alloc.value.refundable > 0,
    })
    toast.ok(`Pembayaran ${rp(form.amount)} dicatat`)
    form.note = ''
    load()
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}

watch(() => props.householdId, load, { immediate: true })
</script>

<template>
  <form class="card max-w-2xl" @submit.prevent="submit">
    <h2 class="card-title">Catat pembayaran</h2>
    <label class="field">
      <span>Kepala keluarga</span>
      <HouseholdPicker :model-value="householdId" @update:model-value="(id) => emit('change', id)" />
    </label>
    <template v-if="householdId">
      <p v-if="credit" class="mb-3 rounded-lg bg-primary-soft px-3 py-2 text-sm text-primary">Saldo titipan KK ini: <b>{{ rp(credit) }}</b> (ikut dipakai).</p>
      <div class="field"><span>Bulan yang dibayar</span></div>
      <BillPicker v-model="selected" v-model:periods="periods" :bills="bills" :prepay="prepay" />
      <p v-if="pendingCount" class="mt-2 text-sm text-warn">
        {{ pendingCount }} tagihan sedang menunggu verifikasi bukti bayar — periksa di tab Verifikasi.
      </p>
      <div class="mt-4 grid grid-cols-2 gap-3">
        <label class="field">
          <span>Uang diterima (Rp)</span>
          <input v-model.number="form.amount" class="input" type="number" min="0" required @input="amountTouched = true" />
        </label>
        <label class="field">
          <span>Metode</span>
          <select v-model="form.method" class="input"><option value="tunai">Tunai</option><option value="transfer">Transfer</option><option value="qris">QRIS</option></select>
        </label>
      </div>
      <AllocationNote :items="items" :received="form.amount" :credit="credit" :refund="form.refund" />
      <label v-if="alloc.refundable > 0" class="mb-4 flex items-center gap-2 text-sm">
        <input v-model="form.refund" type="checkbox" /> Kembalikan kelebihan {{ rp(alloc.refundable) }} ke warga (bukan titipan)
      </label>
      <label class="field"><span>Tanggal bayar</span><input v-model="form.paid_at" class="input" type="date" required :max="todayISO()" /></label>
      <label class="field"><span>Catatan (opsional)</span><input v-model="form.note" class="input" maxlength="255" /></label>
      <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
      <button class="btn btn-primary w-full" :disabled="busy || !items.length">
        {{ items.length ? `Simpan pembayaran ${rp(form.amount)}` : 'Pilih bulan yang dibayar' }}
      </button>
    </template>
  </form>
</template>
