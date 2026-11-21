<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { Dashboard } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { dateTimeLabel, dateLabel, initials, periodLabel, rp } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import LoadState from '@/components/LoadState.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const auth = useAuthStore()
const data = ref<Dashboard | null>(null)
const loading = ref(true)
const error = ref('')
const pendingTotal = computed(() =>
  data.value?.staff ? data.value.staff.pending_proofs + data.value.staff.pending_changes + data.value.staff.pending_registrations : 0,
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await http.get<Dashboard>('/dashboard/')).data
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <LoadState :loading="loading" :error="error" @retry="load">
    <template v-if="data">
      <!-- Sapaan -->
      <section class="card mb-4 border-0 bg-primary text-on-primary">
        <div class="text-sm opacity-85">Selamat datang,</div>
        <div class="text-xl font-bold">{{ auth.user?.name }}</div>
        <div v-if="data.me" class="text-sm opacity-85">Rumah {{ data.me.household_label }}</div>
      </section>

      <!-- Statistik pengurus -->
      <div v-if="data.staff" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="card">
          <div class="text-sm text-muted">Kepala keluarga</div>
          <div class="text-2xl font-bold">{{ data.staff.households }}</div>
          <div class="text-xs text-muted">{{ data.staff.residents }} jiwa</div>
        </div>
        <div class="card">
          <div class="text-sm text-muted">Lunas {{ periodLabel(data.period) }}</div>
          <div class="text-2xl font-bold">{{ data.staff.paid_households }}/{{ data.staff.billed_households }}</div>
          <div class="text-xs text-muted">
            {{ data.staff.billed_households ? Math.round((data.staff.paid_households / data.staff.billed_households) * 100) : 0 }}% KK
          </div>
        </div>
        <div class="card">
          <div class="text-sm text-muted">Pemasukan bulan ini</div>
          <div class="text-xl font-bold">{{ rp(data.staff.income) }}</div>
          <div class="text-xs text-muted">dari {{ rp(data.staff.target) }}</div>
        </div>
        <div class="card">
          <div class="text-sm text-muted">Perlu tindakan</div>
          <div class="text-2xl font-bold" :class="{ 'text-warn': pendingTotal > 0 }">{{ pendingTotal }}</div>
          <div class="text-xs text-muted">{{ data.staff.pending_proofs }} bukti · {{ data.staff.pending_changes }} data · {{ data.staff.pending_registrations }} daftar</div>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <!-- Tindakan pengurus -->
        <section v-if="data.staff" class="card">
          <h2 class="card-title">Perlu tindakan</h2>
          <div class="list">
            <RouterLink to="/iuran?tab=verifikasi" class="flex items-center gap-3 py-3">
              <span class="grid size-10 place-items-center rounded-xl bg-warn-soft text-warn"><AppIcon name="wallet" /></span>
              <span class="flex-1"><b>Verifikasi bukti bayar</b><br /><span class="text-sm text-muted">{{ data.staff.pending_proofs }} bukti menunggu</span></span>
              <AppIcon name="chevron" class="text-muted" />
            </RouterLink>
            <RouterLink to="/pengajuan" class="flex items-center gap-3 py-3">
              <span class="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary"><AppIcon name="inbox" /></span>
              <span class="flex-1"><b>Pengajuan perubahan data</b><br /><span class="text-sm text-muted">{{ data.staff.pending_changes }} pengajuan menunggu</span></span>
              <AppIcon name="chevron" class="text-muted" />
            </RouterLink>
            <RouterLink to="/pendaftaran" class="flex items-center gap-3 py-3">
              <span class="grid size-10 place-items-center rounded-xl bg-ok-soft text-ok"><AppIcon name="userplus" /></span>
              <span class="flex-1"><b>Aktivasi warga baru</b><br /><span class="text-sm text-muted">{{ data.staff.pending_registrations }} pendaftaran menunggu</span></span>
              <AppIcon name="chevron" class="text-muted" />
            </RouterLink>
          </div>
        </section>

        <!-- Iuran saya -->
        <section v-if="data.me" class="card">
          <div class="mb-3 flex items-center justify-between gap-2">
            <h2 class="text-[15px] font-semibold">Iuran {{ periodLabel(data.period, true) }}</h2>
            <StatusBadge :status="data.me.current_status" />
          </div>
          <div class="text-2xl font-bold">{{ rp(data.me.current_bills.reduce((s, b) => s + b.amount, 0)) }}</div>
          <div class="text-sm text-muted">{{ data.me.current_bills.map((b) => b.fee_type_name).join(' + ') || 'Tagihan bulan ini belum dibuat' }}</div>
          <p v-if="data.me.arrears_total" class="mt-2 text-sm font-semibold text-bad">
            Belum dibayar: {{ data.me.arrears_months }} bulan ({{ rp(data.me.arrears_total) }})
          </p>
          <div class="mt-4 flex gap-2">
            <RouterLink v-if="data.me.arrears_total" to="/iuran?tab=unggah" class="btn btn-primary"><AppIcon name="upload" :size="18" />Unggah bukti bayar</RouterLink>
            <RouterLink to="/iuran?tab=riwayat" class="btn">Riwayat</RouterLink>
          </div>
        </section>

        <!-- Tunggakan terbanyak -->
        <section v-if="data.staff?.top_arrears.length" class="card">
          <h2 class="card-title">Tunggakan terbanyak</h2>
          <div class="list">
            <RouterLink
              v-for="t in data.staff.top_arrears"
              :key="t.household_id"
              :to="`/iuran?tab=riwayat&household=${t.household_id}`"
              class="flex items-center gap-3 py-2.5"
            >
              <span class="avatar">{{ initials(t.head_name) }}</span>
              <span class="min-w-0 flex-1"><b class="block truncate">{{ t.head_name }}</b><span class="text-sm text-muted">Rumah {{ t.label }}</span></span>
              <span class="badge badge-bad">{{ t.months }} bln · {{ rp(t.total) }}</span>
            </RouterLink>
          </div>
        </section>

        <!-- Kas RT -->
        <RouterLink to="/kas" class="card flex items-center gap-3 hover:bg-surface-2">
          <span class="grid size-11 flex-none place-items-center rounded-xl bg-primary-soft text-primary"><AppIcon name="cash" :size="22" /></span>
          <span class="flex-1"><span class="block text-sm text-muted">Saldo kas RT</span><b class="text-xl">{{ rp(data.cash_balance) }}</b></span>
          <span class="text-sm text-primary">Laporan</span>
        </RouterLink>

        <!-- Kegiatan -->
        <section class="card">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold">Kegiatan mendatang</h2>
            <RouterLink to="/berita" class="text-sm text-primary">Semua</RouterLink>
          </div>
          <p v-if="!data.upcoming_events.length" class="text-sm text-muted">Belum ada kegiatan terjadwal.</p>
          <div class="list">
            <RouterLink v-for="p in data.upcoming_events" :key="p.id" :to="`/berita/${p.id}`" class="flex gap-3 py-2.5">
              <span class="grid size-10 flex-none place-items-center rounded-xl bg-primary-soft text-primary"><AppIcon name="calendar" /></span>
              <span class="min-w-0"><b class="block">{{ p.title }}</b><span class="text-sm text-muted">{{ dateTimeLabel(p.event_at) }}</span></span>
            </RouterLink>
          </div>
        </section>

        <!-- Berita -->
        <section class="card">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold">Berita terbaru</h2>
            <RouterLink to="/berita" class="text-sm text-primary">Semua</RouterLink>
          </div>
          <p v-if="!data.latest_news.length" class="text-sm text-muted">Belum ada berita.</p>
          <div class="list">
            <RouterLink v-for="p in data.latest_news" :key="p.id" :to="`/berita/${p.id}`" class="block py-2.5">
              <b class="block">{{ p.title }}</b>
              <span class="text-sm text-muted">{{ dateLabel(p.published_at) }}</span>
            </RouterLink>
          </div>
        </section>
      </div>
    </template>
  </LoadState>
</template>
