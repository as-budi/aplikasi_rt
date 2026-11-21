<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { Bill, PayMethod } from '@/api/types'
import { useToast } from '@/stores/toast'
import { rp, todayISO } from '@/utils/format'
import BillPicker from './BillPicker.vue'
import HouseholdPicker from './HouseholdPicker.vue'

const props = defineProps<{ householdId: number | null }>()
const emit = defineEmits<{ change: [id: number] }>()
const toast = useToast()

const bills = ref<Bill[]>([])
const pendingCount = ref(0)
const selected = ref<number[]>([])
const form = reactive<{ method: PayMethod; paid_at: string; note: string }>({ method: 'tunai', paid_at: todayISO(), note: '' })
const busy = ref(false)
const error = ref('')

const total = computed(() => bills.value.filter((b) => selected.value.includes(b.id)).reduce((s, b) => s + b.amount, 0))

async function load() {
  selected.value = []
  bills.value = []
  if (!props.householdId) return
  const all = await fetchAll<Bill>('/bills/', { household: props.householdId })
  bills.value = all.filter((b) => b.status === 'belum_bayar')
  pendingCount.value = all.filter((b) => b.status === 'menunggu_verifikasi').length
}

async function submit() {
  if (!props.householdId || !selected.value.length) return
  busy.value = true
  error.value = ''
  try {
    await http.post('/payments/', { household: props.householdId, bills: selected.value, ...form })
    toast.ok(`Pembayaran ${rp(total.value)} dicatat, tagihan lunas`)
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
      <div class="field"><span>Bulan yang dibayar</span></div>
      <BillPicker v-model="selected" :bills="bills" />
      <p v-if="pendingCount" class="mt-2 text-sm text-warn">
        {{ pendingCount }} tagihan sedang menunggu verifikasi bukti bayar — periksa di tab Verifikasi.
      </p>
      <div class="mt-4 grid grid-cols-2 gap-3">
        <label class="field">
          <span>Metode</span>
          <select v-model="form.method" class="input"><option value="tunai">Tunai</option><option value="transfer">Transfer</option><option value="qris">QRIS</option></select>
        </label>
        <label class="field"><span>Tanggal bayar</span><input v-model="form.paid_at" class="input" type="date" required :max="todayISO()" /></label>
      </div>
      <label class="field"><span>Catatan (opsional)</span><input v-model="form.note" class="input" maxlength="255" /></label>
      <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
      <button class="btn btn-primary w-full" :disabled="busy || !selected.length">
        {{ selected.length ? `Simpan — tandai lunas (${rp(total)})` : 'Pilih bulan yang dibayar' }}
      </button>
    </template>
  </form>
</template>
