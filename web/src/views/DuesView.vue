<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import RecapTab from './dues/RecapTab.vue'
import HistoryTab from './dues/HistoryTab.vue'
import VerifyTab from './dues/VerifyTab.vue'
import RecordTab from './dues/RecordTab.vue'
import UploadTab from './dues/UploadTab.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tabs = computed(() => {
  const t: { key: string; label: string }[] = [
    { key: 'rekap', label: 'Rekap' },
    { key: 'riwayat', label: auth.isStaff ? 'Per KK' : 'Iuran saya' },
  ]
  if (auth.isStaff) t.push({ key: 'verifikasi', label: 'Verifikasi' }, { key: 'catat', label: 'Catat bayar' })
  if (auth.user?.household_id) t.push({ key: 'unggah', label: 'Unggah bukti' })
  return t
})

const tab = computed(() => {
  const q = String(route.query.tab ?? 'rekap')
  return tabs.value.some((t) => t.key === q) ? q : 'rekap'
})

const householdId = computed(() => (route.query.household ? Number(route.query.household) : null))

function go(key: string, household?: number | null) {
  router.replace({ query: { tab: key, ...(household ? { household: String(household) } : {}) } })
}
</script>

<template>
  <div class="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:px-0">
    <button v-for="t in tabs" :key="t.key" class="tab" :class="tab === t.key && 'tab-on'" @click="go(t.key)">{{ t.label }}</button>
  </div>

  <RecapTab v-if="tab === 'rekap'" @select="(id) => go('riwayat', id)" />
  <HistoryTab v-else-if="tab === 'riwayat'" :household-id="householdId" @change="(id) => go('riwayat', id)" />
  <VerifyTab v-else-if="tab === 'verifikasi'" />
  <RecordTab v-else-if="tab === 'catat'" :household-id="householdId" @change="(id) => go('catat', id)" />
  <UploadTab v-else-if="tab === 'unggah'" />
</template>
