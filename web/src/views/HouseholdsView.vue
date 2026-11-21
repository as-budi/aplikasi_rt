<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { errMsg, http } from '@/api/http'
import type { HouseholdListItem, Paginated } from '@/api/types'
import { initials } from '@/utils/format'
import { OCCUPANCY } from '@/utils/labels'
import AppIcon from '@/components/AppIcon.vue'
import ExportButtons from '@/components/ExportButtons.vue'
import BaseModal from '@/components/BaseModal.vue'
import HouseholdForm from '@/components/HouseholdForm.vue'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const router = useRouter()
const rows = ref<HouseholdListItem[]>([])
const loading = ref(true)
const error = ref('')
const q = ref('')
const showInactive = ref(false)
const residence = ref<'' | 'menetap' | 'singgah'>('')
const adding = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { page_size: 500, search: q.value || undefined }
    if (!showInactive.value) params.is_active = true
    if (residence.value) params.residence_status = residence.value
    rows.value = (await http.get<Paginated<HouseholdListItem>>('/households/', { params })).data.results
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
watch([showInactive, residence], load)
onMounted(load)

const open = (id: number) => router.push(`/warga/${id}`)
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <div class="relative min-w-0 flex-1">
      <AppIcon name="search" class="absolute top-1/2 left-3 -translate-y-1/2 text-muted" :size="18" />
      <input v-model="q" class="input pl-10!" type="search" placeholder="Cari nama, blok, atau no. rumah…" />
    </div>
    <button class="btn btn-primary hidden md:inline-flex" @click="adding = true"><AppIcon name="plus" :size="18" />Tambah KK</button>
  </div>
  <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
    <div class="flex flex-wrap items-center gap-3 text-sm text-muted">
      <select v-model="residence" class="input w-auto! py-1! text-sm!" aria-label="Status rumah">
        <option value="">Semua status rumah</option>
        <option value="menetap">Menetap</option>
        <option value="singgah">Rumah singgah</option>
      </select>
      <label class="flex items-center gap-2"><input v-model="showInactive" type="checkbox" /> KK nonaktif (pindah)</label>
    </div>
    <ExportButtons kind="residents" />
  </div>

  <LoadState :loading="loading && !rows.length" :error="error" :empty="!rows.length" empty-text="Tidak ada KK yang cocok." @retry="load">
    <!-- Tabel: tablet & desktop -->
    <div class="card hidden overflow-x-auto p-0! md:block">
      <table class="table">
        <thead>
          <tr><th class="pl-4!">Kepala keluarga</th><th>Rumah</th><th>Hunian</th><th>Jiwa</th><th>No. HP</th><th>Iuran bulan ini</th></tr>
        </thead>
        <tbody>
          <tr v-for="h in rows" :key="h.id" class="cursor-pointer hover:bg-surface-2" @click="open(h.id)">
            <td class="pl-4!">
              <div class="flex items-center gap-3"><span class="avatar">{{ initials(h.head_name) }}</span><b>{{ h.head_name }}</b></div>
            </td>
            <td>{{ h.label }}</td>
            <td>
              {{ OCCUPANCY[h.occupancy] }}
              <span v-if="h.residence_status === 'singgah'" class="badge badge-warn ml-1">Singgah</span>
            </td>
            <td>{{ h.member_count }}</td>
            <td>{{ h.head_phone || '—' }}</td>
            <td>
              <span v-if="!h.is_active" class="badge badge-muted">Nonaktif</span>
              <StatusBadge v-else :status="h.current_status" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Kartu: HP -->
    <div class="space-y-2.5 md:hidden">
      <button v-for="h in rows" :key="h.id" class="card flex w-full items-center gap-3 text-left" @click="open(h.id)">
        <span class="avatar">{{ initials(h.head_name) }}</span>
        <span class="min-w-0 flex-1">
          <b class="block truncate">{{ h.head_name }}</b>
          <span class="text-sm text-muted">
            {{ h.label }} · {{ OCCUPANCY[h.occupancy] }}<template v-if="h.residence_status === 'singgah'"> · <b class="text-warn">singgah</b></template> · {{ h.member_count }} jiwa
          </span>
        </span>
        <span v-if="!h.is_active" class="badge badge-muted">Nonaktif</span>
        <StatusBadge v-else :status="h.current_status" />
      </button>
    </div>
  </LoadState>

  <button
    class="fixed right-4 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-10 grid size-14 place-items-center rounded-2xl bg-primary text-on-primary shadow-lg md:hidden"
    aria-label="Tambah KK"
    @click="adding = true"
  >
    <AppIcon name="plus" :size="26" />
  </button>

  <BaseModal :open="adding" title="Tambah kepala keluarga" @close="adding = false">
    <HouseholdForm v-if="adding" @saved="(id) => router.push(`/warga/${id}`)" />
  </BaseModal>
</template>
