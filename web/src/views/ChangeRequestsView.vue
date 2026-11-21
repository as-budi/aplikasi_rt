<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { errMsg, http } from '@/api/http'
import type { ChangeRequest, Paginated } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel } from '@/utils/format'
import { CHANGE_FIELD } from '@/utils/labels'
import BaseModal from '@/components/BaseModal.vue'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const toast = useToast()
const status = ref<'pending' | 'disetujui' | 'ditolak'>('pending')
const rows = ref<ChangeRequest[]>([])
const loading = ref(true)
const error = ref('')
const rejecting = ref<ChangeRequest | null>(null)
const reason = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = (await http.get<Paginated<ChangeRequest>>('/change-requests/', { params: { status: status.value, page_size: 100 } })).data.results
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

async function approve(r: ChangeRequest) {
  const msg = Object.keys(r.changes).length
    ? 'Setujui dan terapkan perubahan ini ke data warga?'
    : 'Tandai pengajuan ini selesai? (Perubahan dilakukan manual di halaman Data Warga.)'
  if (!confirm(msg)) return
  try {
    await http.post(`/change-requests/${r.id}/approve/`)
    toast.ok('Pengajuan disetujui')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

async function reject() {
  if (!rejecting.value) return
  try {
    await http.post(`/change-requests/${rejecting.value.id}/reject/`, { review_note: reason.value })
    rejecting.value = null
    reason.value = ''
    toast.ok('Pengajuan ditolak')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

watch(status, load)
onMounted(load)
</script>

<template>
  <div class="no-scrollbar mb-4 flex gap-2 overflow-x-auto">
    <button v-for="s in (['pending', 'disetujui', 'ditolak'] as const)" :key="s" class="tab" :class="status === s && 'tab-on'" @click="status = s">
      {{ { pending: 'Menunggu', disetujui: 'Disetujui', ditolak: 'Ditolak' }[s] }}
    </button>
  </div>

  <LoadState :loading="loading" :error="error" :empty="!rows.length" empty-text="Tidak ada pengajuan." @retry="load">
    <div class="grid gap-3 md:grid-cols-2">
      <article v-for="r in rows" :key="r.id" class="card">
        <div class="mb-2 flex items-start justify-between gap-2">
          <div>
            <b>{{ r.resident_name ?? 'Pengajuan umum' }}</b>
            <div class="text-sm text-muted">Rumah {{ r.household_label }} · oleh {{ r.requested_by_name ?? '—' }} · {{ dateLabel(r.created_at) }}</div>
          </div>
          <StatusBadge :status="r.status" />
        </div>
        <table v-if="Object.keys(r.changes).length" class="table mb-2">
          <thead><tr><th>Data</th><th>Lama</th><th>Baru</th></tr></thead>
          <tbody>
            <tr v-for="(c, f) in r.changes" :key="f">
              <td>{{ CHANGE_FIELD[f] ?? f }}</td>
              <td class="text-muted">{{ c.old || '—' }}</td>
              <td class="font-semibold">{{ c.new || '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="r.note" class="mb-2 rounded-lg bg-surface-2 px-3 py-2 text-sm">{{ r.note }}</p>
        <p v-if="r.review_note" class="text-sm text-muted">Catatan: {{ r.review_note }} ({{ r.reviewed_by_name }})</p>
        <div v-if="r.status === 'pending'" class="mt-3 flex gap-2">
          <button class="btn btn-danger flex-1" @click="rejecting = r">Tolak</button>
          <button class="btn btn-primary flex-[2]" @click="approve(r)">Setujui</button>
        </div>
      </article>
    </div>
  </LoadState>

  <BaseModal :open="!!rejecting" title="Tolak pengajuan" @close="rejecting = null">
    <form @submit.prevent="reject">
      <label class="field"><span>Alasan (akan dilihat warga)</span><input v-model="reason" class="input" required placeholder="mis. Mohon lampirkan foto KK terbaru" /></label>
      <button class="btn btn-primary w-full">Tolak pengajuan</button>
    </form>
  </BaseModal>
</template>
