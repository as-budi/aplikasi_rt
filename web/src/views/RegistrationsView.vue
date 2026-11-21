<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { Registration } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel } from '@/utils/format'
import { GENDER, OCCUPANCY, RELATION, RESIDENCE } from '@/utils/labels'
import BaseModal from '@/components/BaseModal.vue'
import DocumentList from '@/components/DocumentList.vue'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import HouseholdPicker from './dues/HouseholdPicker.vue'

const toast = useToast()
const status = ref<'pending' | 'disetujui' | 'ditolak'>('pending')
const rows = ref<Registration[]>([])
const loading = ref(true)
const error = ref('')

const current = ref<Registration | null>(null)
const mode = ref<'new' | 'join'>('new')
const joinHousehold = ref<number | null>(null)
const note = ref('')
const busy = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchAll<Registration>('/registrations/', { status: status.value })
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

function open(r: Registration) {
  current.value = r
  note.value = ''
  mode.value = r.matching_household ? 'join' : 'new'
  joinHousehold.value = r.matching_household?.id ?? null
}

async function approve() {
  if (!current.value) return
  if (mode.value === 'join' && !joinHousehold.value) return toast.error('Pilih KK tujuan.')
  busy.value = true
  try {
    await http.post(`/registrations/${current.value.id}/approve/`, mode.value === 'join' ? { household: joinHousehold.value } : {})
    toast.ok(`Akun ${current.value.username} aktif. Warga sudah bisa masuk.`)
    current.value = null
    load()
  } catch (e) {
    toast.error(errMsg(e))
  } finally {
    busy.value = false
  }
}

async function reject() {
  if (!current.value) return
  if (!note.value.trim()) return toast.error('Tuliskan alasan penolakan.')
  busy.value = true
  try {
    await http.post(`/registrations/${current.value.id}/reject/`, { review_note: note.value })
    toast.ok('Pendaftaran ditolak')
    current.value = null
    load()
  } catch (e) {
    toast.error(errMsg(e))
  } finally {
    busy.value = false
  }
}

watch(status, load)
onMounted(load)
</script>

<template>
  <div class="no-scrollbar mb-4 flex gap-2 overflow-x-auto">
    <button v-for="s in (['pending', 'disetujui', 'ditolak'] as const)" :key="s" class="tab" :class="status === s && 'tab-on'" @click="status = s">
      {{ { pending: 'Menunggu aktivasi', disetujui: 'Diaktifkan', ditolak: 'Ditolak' }[s] }}
    </button>
  </div>

  <LoadState :loading="loading" :error="error" :empty="!rows.length" empty-text="Tidak ada pendaftaran." @retry="load">
    <div class="grid gap-3 md:grid-cols-2">
      <article v-for="r in rows" :key="r.id" class="card">
        <div class="flex items-start justify-between gap-2">
          <div>
            <b>{{ r.name }}</b>
            <div class="text-sm text-muted">Rumah {{ r.house_label }} · @{{ r.username }} · {{ r.phone }}</div>
            <div class="text-xs text-muted">Mendaftar {{ dateLabel(r.created_at) }}</div>
          </div>
          <StatusBadge :status="r.status" />
        </div>
        <template v-if="r.status === 'pending' && r.data.household">
          <p class="mt-2 text-sm">
            {{ r.data.members?.length }} anggota keluarga · {{ OCCUPANCY[r.data.household.occupancy] }} · {{ RESIDENCE[r.data.household.residence_status] }}
          </p>
          <p v-if="r.matching_household" class="mt-1 text-sm text-warn">
            Rumah ini sudah terdaftar atas nama {{ r.matching_household.head_name }}.
          </p>
          <button class="btn btn-primary mt-3 w-full" @click="open(r)">Periksa & aktifkan</button>
        </template>
        <p v-else-if="r.status === 'disetujui'" class="mt-2 text-sm text-muted">
          Diaktifkan oleh {{ r.reviewed_by_name }} ·
          <RouterLink v-if="r.household" :to="`/warga/${r.household}`" class="text-primary">lihat KK {{ r.household_label }}</RouterLink>
        </p>
        <p v-else-if="r.review_note" class="mt-2 text-sm text-muted">Alasan: {{ r.review_note }} ({{ r.reviewed_by_name }})</p>
      </article>
    </div>
  </LoadState>

  <BaseModal :open="!!current" :title="`Pendaftaran ${current?.name ?? ''}`" wide @close="current = null">
    <template v-if="current?.data.household">
      <dl class="mb-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
        <div><dt class="text-muted">Rumah</dt><dd class="font-semibold">{{ current.house_label }}</dd></div>
        <div><dt class="text-muted">No. KK</dt><dd class="font-semibold">{{ current.data.household.no_kk || '—' }}</dd></div>
        <div><dt class="text-muted">Status rumah</dt><dd class="font-semibold">{{ RESIDENCE[current.data.household.residence_status] }}</dd></div>
        <div><dt class="text-muted">Hunian</dt><dd class="font-semibold">{{ OCCUPANCY[current.data.household.occupancy] }}</dd></div>
        <div><dt class="text-muted">Mulai tinggal</dt><dd class="font-semibold">{{ dateLabel(current.data.household.since) }}</dd></div>
        <div><dt class="text-muted">Akun</dt><dd class="font-semibold">@{{ current.username }} · {{ current.phone }}</dd></div>
        <div v-if="current.data.household.address" class="col-span-full"><dt class="text-muted">Alamat</dt><dd class="font-semibold">{{ current.data.household.address }}</dd></div>
      </dl>

      <h3 class="mb-2 text-sm font-semibold">Dokumen (cocokkan dengan isian)</h3>
      <div class="mb-4"><DocumentList :documents="current.documents" /></div>

      <h3 class="mb-1 text-sm font-semibold">Anggota keluarga</h3>
      <div class="list mb-4">
        <div v-for="(m, i) in current.data.members" :key="i" class="py-2 text-sm">
          <b>{{ m.name }}</b> <span v-if="i === 0" class="badge badge-primary">pendaftar</span>
          <div class="text-muted">
            {{ RELATION[m.relation] }} · {{ GENDER[m.gender] }}
            <template v-if="m.birth_date"> · {{ m.birth_place }} {{ dateLabel(m.birth_date) }}</template>
            <template v-if="m.occupation"> · {{ m.occupation }}</template>
          </div>
          <div class="text-xs text-muted">NIK {{ m.nik || '—' }}<template v-if="m.phone"> · {{ m.phone }}</template></div>
        </div>
      </div>

      <fieldset class="mb-4 rounded-xl bg-surface-2 p-3 text-sm">
        <legend class="sr-only">Cara aktivasi</legend>
        <label class="mb-2 flex items-center gap-2">
          <input v-model="mode" type="radio" value="new" :disabled="!!current.matching_household" /> Buat KK baru untuk rumah {{ current.house_label }}
        </label>
        <label class="flex items-center gap-2"><input v-model="mode" type="radio" value="join" /> Gabung ke KK yang sudah ada</label>
        <div v-if="mode === 'join'" class="mt-2"><HouseholdPicker v-model="joinHousehold" /></div>
      </fieldset>

      <label class="field"><span>Alasan (wajib jika ditolak; ditampilkan saat pendaftar mencoba masuk)</span><input v-model="note" class="input" /></label>
      <div class="flex gap-2">
        <button class="btn btn-danger flex-1" :disabled="busy" @click="reject">Tolak</button>
        <button class="btn btn-primary flex-[2]" :disabled="busy" @click="approve">Aktifkan akun</button>
      </div>
    </template>
  </BaseModal>
</template>
