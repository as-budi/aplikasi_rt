<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { Bill, PaymentProof, PrepayOptions } from '@/api/types'
import { useToast } from '@/stores/toast'
import { compressImage } from '@/utils/image'
import { selectedItems } from '@/utils/allocation'
import { dateLabel, periodLabel, rp, todayISO } from '@/utils/format'
import AllocationNote from '@/components/AllocationNote.vue'
import AppIcon from '@/components/AppIcon.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import BillPicker from './BillPicker.vue'

const toast = useToast()
const bills = ref<Bill[]>([])
const prepay = ref<PrepayOptions | null>(null)
const proofs = ref<PaymentProof[]>([])
const selected = ref<number[]>([])
const periods = ref<string[]>([])
const form = reactive({ amount: 0, transfer_date: todayISO(), method: 'transfer', note: '' })
const amountTouched = ref(false)
const file = ref<File | null>(null)
const preview = ref('')
const busy = ref(false)
const error = ref('')

const credit = computed(() => prepay.value?.credit ?? 0)
const items = computed(() => selectedItems(bills.value, selected.value, periods.value, prepay.value?.monthly_total ?? 0))
const total = computed(() => items.value.reduce((s, i) => s + i.amount, 0))
// Saran nominal: total bulan terpilih dikurangi saldo titipan (selama belum diubah manual)
watch(total, (t) => {
  if (!amountTouched.value) form.amount = Math.max(0, t - credit.value)
})

async function load() {
  const [b, p, o] = await Promise.all([
    fetchAll<Bill>('/bills/', { mine: 1, status: 'belum_bayar' }),
    fetchAll<PaymentProof>('/payment-proofs/', { mine: 1 }),
    http.get<PrepayOptions>('/bills/prepay-options/'),
  ])
  bills.value = b
  proofs.value = p.slice(0, 10)
  prepay.value = o.data
  selected.value = []
  periods.value = []
  amountTouched.value = false
}

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (!f) return
  if (f.size > 15 * 1024 * 1024) {
    error.value = 'File terlalu besar.'
    return
  }
  file.value = await compressImage(f)
  if (file.value.size > 5 * 1024 * 1024) {
    error.value = 'Ukuran file maksimal 5 MB.'
    file.value = null
    return
  }
  error.value = ''
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = file.value.type.startsWith('image/') ? URL.createObjectURL(file.value) : ''
}

async function submit() {
  if (!items.value.length) return (error.value = 'Pilih bulan yang dibayar.')
  if (!form.amount || form.amount < 1) return (error.value = 'Isi nominal yang Anda transfer.')
  if (!file.value) return (error.value = 'Lampirkan foto atau screenshot bukti transfer.')
  busy.value = true
  error.value = ''
  try {
    const fd = new FormData()
    selected.value.forEach((id) => fd.append('bills', String(id)))
    periods.value.forEach((p) => fd.append('periods', p))
    fd.append('file', file.value)
    fd.append('amount', String(form.amount))
    fd.append('transfer_date', form.transfer_date)
    fd.append('method', form.method)
    fd.append('note', form.note)
    await http.post('/payment-proofs/', fd)
    toast.ok('Bukti terkirim. Pengurus akan memverifikasi.')
    file.value = null
    preview.value = ''
    form.note = ''
    load()
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-[3fr_2fr]">
    <form class="card" @submit.prevent="submit">
      <h2 class="card-title">Unggah bukti pembayaran</h2>
      <p class="mb-3 text-sm text-muted">Satu bukti transfer boleh untuk beberapa bulan sekaligus, termasuk bayar di muka.</p>
      <p v-if="credit" class="mb-3 rounded-lg bg-primary-soft px-3 py-2 text-sm text-primary">
        Anda punya <b>saldo titipan {{ rp(credit) }}</b> dari pembayaran sebelumnya; otomatis ikut dipakai.
      </p>
      <div class="field"><span>Bulan yang dibayar</span></div>
      <BillPicker v-model="selected" v-model:periods="periods" :bills="bills" :prepay="prepay" />

      <div class="mt-4 grid grid-cols-2 gap-3">
        <label class="field">
          <span>Nominal yang Anda transfer (Rp)</span>
          <input v-model.number="form.amount" class="input" type="number" min="1" required @input="amountTouched = true" />
        </label>
        <label class="field">
          <span>Metode</span>
          <select v-model="form.method" class="input"><option value="transfer">Transfer</option><option value="qris">QRIS</option></select>
        </label>
      </div>
      <AllocationNote :items="items" :received="form.amount" :credit="credit" who="warga" />
      <label class="field"><span>Tanggal transfer</span><input v-model="form.transfer_date" class="input" type="date" required :max="todayISO()" /></label>

      <label class="field">
        <span>Foto / screenshot bukti</span>
        <span
          class="flex cursor-pointer flex-col items-center gap-1 rounded-xl border-2 border-dashed border-line p-5 text-center text-muted hover:border-primary hover:text-primary"
        >
          <img v-if="preview" :src="preview" alt="Pratinjau bukti" class="mb-2 max-h-48 rounded-lg" />
          <AppIcon v-else name="upload" :size="28" />
          <span>{{ file ? file.name : 'Ketuk untuk ambil foto atau pilih file' }}</span>
          <span class="text-xs">JPG, PNG, WEBP, atau PDF · maks. 5 MB</span>
          <input type="file" accept="image/*,application/pdf" class="sr-only" @change="onFile" />
        </span>
      </label>
      <label class="field"><span>Catatan (opsional)</span><input v-model="form.note" class="input" maxlength="255" placeholder="mis. transfer dari rekening istri" /></label>
      <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
      <button class="btn btn-primary w-full" :disabled="busy || !items.length">
        {{ busy ? 'Mengirim…' : `Kirim bukti${form.amount ? ' · ' + rp(form.amount) : ''}` }}
      </button>
    </form>

    <section class="card self-start">
      <h2 class="card-title">Bukti yang pernah dikirim</h2>
      <p v-if="!proofs.length" class="text-sm text-muted">Belum ada.</p>
      <div class="list">
        <div v-for="p in proofs" :key="p.id" class="py-2.5">
          <div class="flex items-center justify-between gap-2">
            <b>{{ [...new Set(p.bills.map((b) => periodLabel(b.period)))].join(', ') || 'Titipan' }}</b>
            <StatusBadge :status="p.status" />
          </div>
          <div class="text-sm text-muted">{{ rp(p.amount) }} · dikirim {{ dateLabel(p.created_at) }}</div>
          <div v-if="p.review_note" class="text-sm" :class="p.status === 'ditolak' ? 'text-bad' : 'text-muted'">{{ p.review_note }}</div>
        </div>
      </div>
    </section>
  </div>
</template>
