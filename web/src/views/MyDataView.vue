<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { ChangeRequest, HouseholdOwn, Paginated, Resident } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel, initials } from '@/utils/format'
import { CHANGE_FIELD, GENDER, MARITAL, OCCUPANCY, RELATION, RELIGIONS } from '@/utils/labels'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const toast = useToast()
const hh = ref<HouseholdOwn | null>(null)
const requests = ref<ChangeRequest[]>([])
const loading = ref(true)
const error = ref('')

const editing = ref<Resident | null>(null)
const form = reactive({ name: '', nik: '', gender: 'L', birth_place: '', birth_date: '', phone: '', occupation: '', religion: '', marital_status: '' })
const formError = ref('')
const busy = ref(false)

const noteOpen = ref(false)
const note = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    hh.value = (await http.get<HouseholdOwn>('/me/household/')).data
    requests.value = (await http.get<Paginated<ChangeRequest>>('/change-requests/', { params: { mine: 1, page_size: 20 } })).data.results
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

function edit(m: Resident) {
  editing.value = m
  Object.assign(form, {
    name: m.name, nik: '', gender: m.gender, birth_place: m.birth_place, birth_date: m.birth_date ?? '',
    phone: m.phone, occupation: m.occupation, religion: m.religion, marital_status: m.marital_status,
  })
  formError.value = ''
}

async function save() {
  const m = editing.value
  if (!m) return
  // Kirim hanya field yang berubah
  const changed: Record<string, string | null> = {}
  for (const key of ['name', 'gender', 'birth_place', 'phone', 'occupation', 'religion', 'marital_status'] as const) {
    if ((form[key] ?? '') !== ((m as unknown as Record<string, string>)[key] ?? '')) changed[key] = form[key]
  }
  if ((form.birth_date || null) !== m.birth_date) changed.birth_date = form.birth_date || null
  if (form.nik.trim()) changed.nik = form.nik.trim()
  if (!Object.keys(changed).length) {
    editing.value = null
    return
  }
  busy.value = true
  formError.value = ''
  try {
    const { data } = await http.patch<{ applied: string[]; change_request: ChangeRequest | null }>(`/me/residents/${m.id}/`, changed)
    editing.value = null
    if (data.change_request) toast.ok('Perubahan identitas dikirim ke pengurus untuk disetujui')
    else toast.ok('Data tersimpan')
    load()
  } catch (e) {
    formError.value = errMsg(e)
  } finally {
    busy.value = false
  }
}

async function sendNote() {
  try {
    await http.post('/change-requests/', { note: note.value })
    noteOpen.value = false
    note.value = ''
    toast.ok('Pengajuan terkirim ke pengurus')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

onMounted(load)
</script>

<template>
  <LoadState :loading="loading && !hh" :error="error" @retry="load">
    <template v-if="hh">
      <section class="card mb-4">
        <div class="text-sm text-muted">Keluarga</div>
        <div class="text-lg font-bold">Rumah {{ hh.label }}</div>
        <dl class="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div><dt class="text-muted">No. KK</dt><dd class="font-semibold">{{ hh.no_kk_masked || '—' }}</dd></div>
          <div><dt class="text-muted">Status hunian</dt><dd class="font-semibold">{{ OCCUPANCY[hh.occupancy] }}</dd></div>
        </dl>
      </section>

      <section class="card mb-4">
        <div class="mb-2 flex items-center justify-between gap-2">
          <h2 class="text-[15px] font-semibold">Anggota keluarga</h2>
          <button class="btn btn-sm" @click="noteOpen = true"><AppIcon name="plus" :size="16" />Ajukan lainnya</button>
        </div>
        <div class="list">
          <div v-for="m in hh.members" :key="m.id" class="flex items-center gap-3 py-3">
            <span class="avatar">{{ initials(m.name) }}</span>
            <div class="min-w-0 flex-1">
              <div class="font-semibold">{{ m.name }}</div>
              <div class="text-sm text-muted">
                {{ RELATION[m.relation] }} · {{ GENDER[m.gender] }}<template v-if="m.age !== null"> · {{ m.age }} th</template>
              </div>
              <div class="text-xs text-muted">NIK {{ m.nik_masked || '—' }}<template v-if="m.phone"> · {{ m.phone }}</template></div>
            </div>
            <button class="btn btn-sm" @click="edit(m)"><AppIcon name="edit" :size="16" />Ubah</button>
          </div>
        </div>
      </section>

      <section class="card">
        <h2 class="card-title">Riwayat pengajuan</h2>
        <p v-if="!requests.length" class="text-sm text-muted">Belum ada pengajuan.</p>
        <div class="list">
          <div v-for="r in requests" :key="r.id" class="py-3">
            <div class="flex items-center justify-between gap-2">
              <b>{{ r.resident_name ?? 'Pengajuan umum' }}</b>
              <StatusBadge :status="r.status" />
            </div>
            <ul class="mt-1 text-sm text-muted">
              <li v-for="(c, f) in r.changes" :key="f">{{ CHANGE_FIELD[f] ?? f }}: {{ c.old || '—' }} → <b class="text-ink">{{ c.new || '—' }}</b></li>
              <li v-if="r.note">{{ r.note }}</li>
            </ul>
            <div class="text-xs text-muted">{{ dateLabel(r.created_at) }}<template v-if="r.review_note"> · Catatan pengurus: {{ r.review_note }}</template></div>
          </div>
        </div>
      </section>
    </template>
  </LoadState>

  <BaseModal :open="!!editing" :title="`Ubah data ${editing?.name ?? ''}`" wide @close="editing = null">
    <form @submit.prevent="save">
      <p class="mb-4 rounded-lg bg-primary-soft px-3 py-2 text-sm text-primary">
        No. HP, pekerjaan, agama, dan status perkawinan langsung tersimpan. Nama, NIK, jenis kelamin, dan tempat/tanggal lahir akan
        <b>ditinjau pengurus</b> dulu.
      </p>
      <div class="grid gap-x-3 md:grid-cols-2">
        <label class="field"><span>No. HP</span><input v-model="form.phone" class="input" type="tel" maxlength="20" /></label>
        <label class="field"><span>Pekerjaan</span><input v-model="form.occupation" class="input" maxlength="60" /></label>
        <label class="field">
          <span>Agama</span>
          <select v-model="form.religion" class="input"><option value="">—</option><option v-for="x in RELIGIONS" :key="x">{{ x }}</option></select>
        </label>
        <label class="field">
          <span>Status perkawinan</span>
          <select v-model="form.marital_status" class="input"><option value="">—</option><option v-for="x in MARITAL" :key="x">{{ x }}</option></select>
        </label>
      </div>
      <hr class="my-2 mb-4 border-line" />
      <div class="grid gap-x-3 md:grid-cols-2">
        <label class="field"><span>Nama lengkap</span><input v-model="form.name" class="input" required maxlength="100" /></label>
        <label class="field">
          <span>NIK baru (isi hanya jika ada koreksi)</span>
          <input v-model="form.nik" class="input" inputmode="numeric" maxlength="16" pattern="\d{16}" :placeholder="editing?.nik_masked" />
        </label>
        <label class="field">
          <span>Jenis kelamin</span>
          <select v-model="form.gender" class="input"><option v-for="(l, k) in GENDER" :key="k" :value="k">{{ l }}</option></select>
        </label>
        <label class="field"><span>Tempat lahir</span><input v-model="form.birth_place" class="input" maxlength="60" /></label>
        <label class="field"><span>Tanggal lahir</span><input v-model="form.birth_date" class="input" type="date" /></label>
      </div>
      <p v-if="formError" class="mb-3 text-sm text-bad" role="alert">{{ formError }}</p>
      <button class="btn btn-primary w-full" :disabled="busy">{{ busy ? 'Mengirim…' : 'Simpan' }}</button>
    </form>
  </BaseModal>

  <BaseModal :open="noteOpen" title="Ajukan perubahan lain" @close="noteOpen = false">
    <form @submit.prevent="sendNote">
      <p class="mb-3 text-sm text-muted">Misalnya menambah anggota keluarga baru, pindah rumah, atau anggota yang meninggal.</p>
      <label class="field"><span>Keterangan</span><textarea v-model="note" class="input" rows="4" required /></label>
      <button class="btn btn-primary w-full">Kirim ke pengurus</button>
    </form>
  </BaseModal>
</template>
