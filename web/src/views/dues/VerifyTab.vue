<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { PaymentProof } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel, initials, periodLabel, rp } from '@/utils/format'
import { METHOD } from '@/utils/labels'
import BaseModal from '@/components/BaseModal.vue'
import LoadState from '@/components/LoadState.vue'

const toast = useToast()
const proofs = ref<PaymentProof[]>([])
const loading = ref(true)
const error = ref('')
const current = ref<PaymentProof | null>(null)
const note = ref('')
const busy = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    proofs.value = await fetchAll<PaymentProof>('/payment-proofs/', { status: 'pending' })
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

const billTotal = (p: PaymentProof) => p.bills.reduce((s, b) => s + b.amount, 0)
const months = (p: PaymentProof) => [...new Set(p.bills.map((b) => periodLabel(b.period)))].join(', ')

function open(p: PaymentProof) {
  current.value = p
  note.value = ''
}

async function decide(action: 'approve' | 'reject') {
  if (!current.value) return
  busy.value = true
  try {
    await http.post(`/payment-proofs/${current.value.id}/${action}/`, { review_note: note.value })
    toast.ok(action === 'approve' ? 'Pembayaran diterima, tagihan lunas' : 'Bukti ditolak, warga bisa mengunggah ulang')
    current.value = null
    load()
  } catch (e) {
    toast.error(errMsg(e))
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <LoadState :loading="loading" :error="error" :empty="!proofs.length" empty-text="Semua bukti bayar sudah diverifikasi." @retry="load">
    <div class="grid gap-3 md:grid-cols-2">
      <button v-for="p in proofs" :key="p.id" class="card flex items-center gap-3 text-left hover:bg-surface-2" @click="open(p)">
        <span class="avatar">{{ initials(p.head_name) }}</span>
        <span class="min-w-0 flex-1">
          <b class="block truncate">{{ p.head_name }} · {{ p.household_label }}</b>
          <span class="text-sm text-muted">{{ months(p) }} · {{ rp(p.amount) }} · {{ METHOD[p.method] }}</span>
          <span class="block text-xs text-muted">Diunggah {{ dateLabel(p.created_at) }}</span>
        </span>
        <span class="btn btn-sm">Periksa</span>
      </button>
    </div>
  </LoadState>

  <BaseModal :open="!!current" :title="`Bukti bayar · ${current?.head_name ?? ''}`" wide @close="current = null">
    <template v-if="current">
      <div class="mb-4 overflow-hidden rounded-xl border border-line bg-surface-2">
        <img v-if="current.file_type === 'image'" :src="current.file_url" alt="Bukti pembayaran" class="mx-auto max-h-[50vh] object-contain" />
        <a v-else :href="current.file_url" target="_blank" rel="noopener" class="block p-6 text-center text-primary">Buka bukti (PDF)</a>
      </div>
      <dl class="list mb-4 text-sm">
        <div class="flex justify-between py-2"><dt class="text-muted">Rumah</dt><dd class="font-semibold">{{ current.household_label }}</dd></div>
        <div class="flex justify-between gap-4 py-2">
          <dt class="text-muted">Tagihan</dt>
          <dd class="text-right font-semibold">{{ months(current) }} ({{ current.bills.length }} item, {{ rp(billTotal(current)) }})</dd>
        </div>
        <div class="flex justify-between py-2">
          <dt class="text-muted">Nominal transfer</dt>
          <dd class="font-semibold" :class="current.amount !== billTotal(current) && 'text-warn'">
            {{ rp(current.amount) }}<template v-if="current.amount !== billTotal(current)"> (tidak sama)</template>
          </dd>
        </div>
        <div class="flex justify-between py-2"><dt class="text-muted">Tanggal / metode</dt><dd class="font-semibold">{{ dateLabel(current.transfer_date) }} · {{ METHOD[current.method] }}</dd></div>
        <div v-if="current.note" class="py-2"><dt class="text-muted">Catatan warga</dt><dd>{{ current.note }}</dd></div>
      </dl>
      <label class="field"><span>Catatan (wajib jika ditolak)</span><input v-model="note" class="input" placeholder="mis. nominal tidak sesuai" /></label>
      <div class="flex gap-2">
        <button class="btn btn-danger flex-1" :disabled="busy" @click="decide('reject')">Tolak</button>
        <button class="btn btn-primary flex-[2]" :disabled="busy" @click="decide('approve')">Terima — tandai lunas</button>
      </div>
    </template>
  </BaseModal>
</template>
