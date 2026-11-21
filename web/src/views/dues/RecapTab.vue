<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { errMsg, http } from '@/api/http'
import type { Summary } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import { currentPeriod, currentYear, monthShort, periodLabel, rp } from '@/utils/format'
import ExportButtons from '@/components/ExportButtons.vue'
import LoadState from '@/components/LoadState.vue'
import StatusDot from '@/components/StatusDot.vue'

const emit = defineEmits<{ select: [householdId: number] }>()
const auth = useAuthStore()
const toast = useToast()

const year = ref(currentYear())
const data = ref<Summary | null>(null)
const loading = ref(true)
const error = ref('')
const years = [currentYear(), currentYear() - 1, currentYear() - 2]

// Tampilkan bulan sampai bulan berjalan saja (untuk tahun ini)
const periods = computed(() => (data.value?.periods ?? []).filter((p) => p <= currentPeriod()))
const totalIncome = computed(() => periods.value.reduce((s, p) => s + (data.value?.income?.[p] ?? 0), 0))

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await http.get<Summary>('/bills/summary/', { params: { year: year.value } })).data
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
  // Di HP tabel lebih lebar dari layar: tampilkan bulan terbaru lebih dulu
  await nextTick()
  if (scroller.value) scroller.value.scrollLeft = scroller.value.scrollWidth
}

const scroller = ref<HTMLElement | null>(null)

async function generate() {
  const period = currentPeriod()
  if (!confirm(`Buat tagihan ${periodLabel(period, true)} untuk semua KK aktif? Tagihan yang sudah ada tidak akan digandakan.`)) return
  try {
    const { data: res } = await http.post<{ created: number }>('/bills/generate/', { period })
    toast.ok(`${res.created} tagihan baru dibuat`)
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

watch(year, load)
onMounted(load)
</script>

<template>
  <div class="card">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <h2 class="text-[15px] font-semibold">Rekap iuran</h2>
        <select v-model="year" class="input w-auto! py-1! text-sm!"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select>
      </div>
      <div class="flex flex-wrap items-center gap-3 text-xs text-muted">
        <span class="flex items-center gap-1"><StatusDot status="lunas" /> Lunas</span>
        <span class="flex items-center gap-1"><StatusDot status="menunggu_verifikasi" /> Menunggu</span>
        <span class="flex items-center gap-1"><StatusDot status="belum_bayar" /> Belum</span>
        <button v-if="auth.isStaff && year === currentYear()" class="btn btn-sm" @click="generate">Buat tagihan bulan ini</button>
        <ExportButtons v-if="auth.isStaff" kind="dues" :year="year" />
      </div>
    </div>
    <p v-if="!auth.isStaff" class="mb-3 text-sm text-muted">
      Demi privasi, rekap untuk warga hanya menampilkan rumah, nama kepala keluarga, dan status bayar.
    </p>

    <LoadState :loading="loading" :error="error" :empty="!data?.rows.length" empty-text="Belum ada data iuran." @retry="load">
      <div v-if="data" ref="scroller" class="-mx-4 overflow-x-auto md:mx-0">
        <table class="table min-w-max">
          <thead>
            <tr>
              <th class="sticky left-0 z-[1] bg-surface pl-4! md:pl-2!">Rumah</th>
              <th v-for="p in periods" :key="p" class="text-center!">{{ monthShort(p) }}</th>
              <th v-if="auth.isStaff" class="text-right!">Tunggakan</th>
              <th v-if="auth.isStaff" class="text-right!">Titipan</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in data.rows"
              :key="r.household_id"
              :class="auth.isStaff && 'cursor-pointer hover:bg-surface-2'"
              @click="auth.isStaff && emit('select', r.household_id)"
            >
              <td class="sticky left-0 z-[1] bg-surface pl-4! md:pl-2!">
                <b>{{ r.label }}</b> <span class="text-sm text-muted">{{ r.head_name }}</span>
              </td>
              <td v-for="p in periods" :key="p" class="text-center!"><StatusDot :status="r.cells[p]" /></td>
              <td v-if="auth.isStaff" class="text-right!">
                <span v-if="r.arrears" class="badge badge-bad">{{ rp(r.arrears) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td v-if="auth.isStaff" class="text-right!">
                <span v-if="r.credit" class="badge badge-primary">{{ rp(r.credit) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
            </tr>
          </tbody>
          <tfoot v-if="data.income">
            <tr>
              <td class="sticky left-0 z-[1] bg-surface pl-4! font-semibold md:pl-2!">Pemasukan</td>
              <td v-for="p in periods" :key="p" class="text-center! text-xs font-semibold">{{ Math.round((data.income[p] ?? 0) / 1000) }}rb</td>
              <td class="text-right! font-bold">{{ rp(totalIncome) }}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </LoadState>
  </div>
</template>
