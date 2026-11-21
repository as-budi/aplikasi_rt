<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errMsg, http } from '@/api/http'
import type { HouseholdDetail, Resident } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel, initials } from '@/utils/format'
import { GENDER, OCCUPANCY, RELATION, RESIDENT_STATUS } from '@/utils/labels'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import HouseholdForm from '@/components/HouseholdForm.vue'
import LoadState from '@/components/LoadState.vue'
import ResidentForm from '@/components/ResidentForm.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const id = Number(route.params.id)

const hh = ref<HouseholdDetail | null>(null)
const loading = ref(true)
const error = ref('')

const editingHousehold = ref(false)
const residentModal = ref<{ open: boolean; resident?: Resident }>({ open: false })
const accountFor = ref<Resident | null>(null)
const account = reactive({ username: '', password: '' })
const accountError = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    hh.value = (await http.get<HouseholdDetail>(`/households/${id}/`)).data
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

function onHouseholdSaved() {
  editingHousehold.value = false
  toast.ok('Data KK tersimpan')
  load()
}

function onResidentSaved() {
  residentModal.value = { open: false }
  toast.ok('Data anggota keluarga tersimpan')
  load()
}

async function setActive(active: boolean) {
  const msg = active ? 'Aktifkan kembali KK ini?' : 'Nonaktifkan KK ini (misalnya pindah)? Riwayat iuran tetap tersimpan dan tagihan baru tidak dibuat lagi.'
  if (!hh.value || !confirm(msg)) return
  try {
    if (active) await http.patch(`/households/${id}/`, { is_active: true })
    else await http.delete(`/households/${id}/`)
    toast.ok(active ? 'KK diaktifkan' : 'KK dinonaktifkan')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

async function removeResident(r: Resident) {
  if (!confirm(`Hapus ${r.name} dari data? Untuk warga yang pindah atau meninggal, lebih baik ubah statusnya.`)) return
  try {
    await http.delete(`/residents/${r.id}/`)
    toast.ok('Anggota keluarga dihapus')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

function openAccount(r: Resident) {
  accountFor.value = r
  account.username = (r.phone || r.name.split(' ')[0]).toLowerCase().replace(/[^a-z0-9]/g, '')
  account.password = ''
  accountError.value = ''
}

async function createAccount() {
  if (!accountFor.value) return
  accountError.value = ''
  try {
    await http.post(`/residents/${accountFor.value.id}/create-account/`, account)
    toast.ok(`Akun ${account.username} dibuat. Berikan kata sandi kepada warga.`)
    accountFor.value = null
    load()
  } catch (e) {
    accountError.value = errMsg(e)
  }
}

onMounted(load)
</script>

<template>
  <button class="mb-3 inline-flex items-center gap-1 text-sm text-muted hover:text-ink" @click="router.back()">
    <AppIcon name="back" :size="18" /> Kembali
  </button>

  <LoadState :loading="loading && !hh" :error="error" @retry="load">
    <template v-if="hh">
      <section class="card mb-4">
        <div class="flex items-start gap-3">
          <span class="avatar size-13! text-lg!">{{ initials(hh.head_name) }}</span>
          <div class="min-w-0 flex-1">
            <div class="text-lg font-bold">{{ hh.head_name }}</div>
            <div class="text-sm text-muted">Rumah {{ hh.label }} · {{ OCCUPANCY[hh.occupancy] }}</div>
          </div>
          <span v-if="!hh.is_active" class="badge badge-muted">Nonaktif</span>
          <StatusBadge v-else :status="hh.current_status" />
        </div>
        <dl class="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div><dt class="text-muted">No. KK</dt><dd class="font-semibold">{{ hh.no_kk || '—' }}</dd></div>
          <div><dt class="text-muted">Tinggal sejak</dt><dd class="font-semibold">{{ dateLabel(hh.since) }}</dd></div>
          <div class="col-span-2"><dt class="text-muted">Alamat</dt><dd class="font-semibold">{{ hh.address || '—' }}</dd></div>
        </dl>
        <div class="mt-4 flex flex-wrap gap-2">
          <button class="btn btn-sm" @click="editingHousehold = true"><AppIcon name="edit" :size="16" />Ubah</button>
          <RouterLink :to="`/iuran?tab=riwayat&household=${hh.id}`" class="btn btn-sm"><AppIcon name="wallet" :size="16" />Riwayat iuran</RouterLink>
          <RouterLink :to="`/iuran?tab=catat&household=${hh.id}`" class="btn btn-sm">Catat bayar</RouterLink>
          <button v-if="hh.is_active" class="btn btn-sm btn-danger" @click="setActive(false)">Nonaktifkan</button>
          <button v-else class="btn btn-sm" @click="setActive(true)">Aktifkan</button>
        </div>
      </section>

      <section class="card">
        <div class="mb-2 flex items-center justify-between">
          <h2 class="text-[15px] font-semibold">Anggota keluarga ({{ hh.members.length }})</h2>
          <button class="btn btn-sm btn-primary" @click="residentModal = { open: true }"><AppIcon name="plus" :size="16" />Tambah</button>
        </div>
        <p v-if="!hh.members.length" class="py-4 text-sm text-muted">Belum ada anggota keluarga.</p>
        <div class="list">
          <div v-for="m in hh.members" :key="m.id" class="flex flex-wrap items-center gap-3 py-3">
            <span class="avatar">{{ initials(m.name) }}</span>
            <div class="min-w-0 flex-1">
              <div class="font-semibold">
                {{ m.name }}
                <span v-if="m.status !== 'aktif'" class="badge badge-muted ml-1">{{ RESIDENT_STATUS[m.status] }}</span>
              </div>
              <div class="text-sm text-muted">
                {{ RELATION[m.relation] }} · {{ GENDER[m.gender] }}<template v-if="m.age !== null"> · {{ m.age }} th</template>
                <template v-if="m.phone"> · {{ m.phone }}</template>
              </div>
              <div class="text-xs text-muted">NIK {{ m.nik || '—' }}<template v-if="m.username"> · akun: <b>{{ m.username }}</b></template></div>
            </div>
            <div class="flex gap-1">
              <button v-if="!m.has_account && m.status === 'aktif'" class="btn btn-sm" @click="openAccount(m)">Buat akun</button>
              <button class="btn-icon" aria-label="Ubah" @click="residentModal = { open: true, resident: m }"><AppIcon name="edit" :size="18" /></button>
              <button class="btn-icon" aria-label="Hapus" @click="removeResident(m)"><AppIcon name="x" :size="18" /></button>
            </div>
          </div>
        </div>
      </section>

      <BaseModal :open="editingHousehold" title="Ubah data KK" @close="editingHousehold = false">
        <HouseholdForm v-if="editingHousehold" :initial="hh" @saved="onHouseholdSaved" />
      </BaseModal>

      <BaseModal
        :open="residentModal.open"
        :title="residentModal.resident ? 'Ubah anggota keluarga' : 'Tambah anggota keluarga'"
        wide
        @close="residentModal = { open: false }"
      >
        <ResidentForm v-if="residentModal.open" :household-id="hh.id" :resident="residentModal.resident" @saved="onResidentSaved" />
      </BaseModal>

      <BaseModal :open="!!accountFor" :title="`Buat akun untuk ${accountFor?.name ?? ''}`" @close="accountFor = null">
        <form @submit.prevent="createAccount">
          <p class="mb-4 text-sm text-muted">Warga masuk dengan username (atau no. HP) dan kata sandi ini, lalu bisa menggantinya di menu Akun.</p>
          <label class="field"><span>Username</span><input v-model="account.username" class="input" required autocapitalize="none" /></label>
          <label class="field"><span>Kata sandi awal (min. 8 karakter)</span><input v-model="account.password" class="input" required minlength="8" /></label>
          <p v-if="accountError" class="mb-3 text-sm text-bad" role="alert">{{ accountError }}</p>
          <button class="btn btn-primary w-full">Buat akun</button>
        </form>
      </BaseModal>
    </template>
  </LoadState>
</template>
