<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { errMsg, fetchAll, http } from '@/api/http'
import type { CashEntry, CashKind, CashReport } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import { currentPeriod, currentYear, dateLabel, monthShort, periodLabel, rp, todayISO } from '@/utils/format'
import { CASH_CATEGORY, INCOME_ONLY } from '@/utils/labels'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import ExportButtons from '@/components/ExportButtons.vue'
import LoadState from '@/components/LoadState.vue'

const auth = useAuthStore()
const toast = useToast()

const year = ref(currentYear())
const years = [currentYear(), currentYear() - 1, currentYear() - 2]
const month = ref<number | ''>('')
const kind = ref<CashKind | ''>('')
const report = ref<CashReport | null>(null)
const entries = ref<CashEntry[]>([])
const loading = ref(true)
const error = ref('')

const months = computed(() =>
  (report.value?.months ?? []).filter((m) => year.value < currentYear() || m.period <= currentPeriod()),
)
const maxBar = computed(() => Math.max(1, ...months.value.map((m) => Math.max(m.iuran + m.other_income, m.expense))))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [r, e] = await Promise.all([
      http.get<CashReport>('/cash-entries/report/', { params: { year: year.value } }),
      fetchAll<CashEntry>('/cash-entries/', { year: year.value, month: month.value || undefined, kind: kind.value || undefined }),
    ])
    report.value = r.data
    entries.value = e
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

// ---------- Form transaksi (pengurus) ----------
const modal = ref<{ open: boolean; entry?: CashEntry }>({ open: false })
const form = reactive({ kind: 'pengeluaran' as CashKind, category: 'kebersihan', description: '', amount: 0, date: todayISO() })
const receipt = ref<File | null>(null)
const formError = ref('')
const busy = ref(false)
const categories = computed(() =>
  Object.entries(CASH_CATEGORY).filter(([k]) => form.kind === 'pemasukan' || !INCOME_ONLY.includes(k)),
)
watch(() => form.kind, (k) => {
  if (k === 'pengeluaran' && INCOME_ONLY.includes(form.category)) form.category = 'lainnya'
})

function openForm(entry?: CashEntry) {
  modal.value = { open: true, entry }
  Object.assign(form, entry
    ? { kind: entry.kind, category: entry.category, description: entry.description, amount: entry.amount, date: entry.date }
    : { kind: 'pengeluaran', category: 'kebersihan', description: '', amount: 0, date: todayISO() })
  receipt.value = null
  formError.value = ''
}

async function save() {
  busy.value = true
  formError.value = ''
  try {
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => fd.append(k, String(v)))
    if (receipt.value) fd.append('receipt', receipt.value)
    const id = modal.value.entry?.id
    if (id) await http.patch(`/cash-entries/${id}/`, fd)
    else await http.post('/cash-entries/', fd)
    toast.ok('Transaksi kas tersimpan')
    modal.value = { open: false }
    load()
  } catch (e) {
    formError.value = errMsg(e)
  } finally {
    busy.value = false
  }
}

async function remove(entry: CashEntry) {
  if (!confirm(`Hapus transaksi "${entry.description}" (${rp(entry.amount)})?`)) return
  try {
    await http.delete(`/cash-entries/${entry.id}/`)
    toast.ok('Transaksi dihapus')
    load()
  } catch (e) {
    toast.error(errMsg(e))
  }
}

watch([year, month, kind], load)
onMounted(load)
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
    <select v-model="year" class="input w-auto!" aria-label="Tahun"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select>
    <div class="flex flex-wrap gap-2">
      <ExportButtons kind="cash" :year="year" />
      <button v-if="auth.isStaff" class="btn btn-sm btn-primary" @click="openForm()"><AppIcon name="plus" :size="16" />Catat transaksi</button>
    </div>
  </div>

  <LoadState :loading="loading && !report" :error="error" @retry="load">
    <template v-if="report">
      <!-- Ringkasan -->
      <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="card"><div class="text-sm text-muted">Saldo awal {{ year }}</div><div class="text-lg font-bold md:text-xl">{{ rp(report.opening_balance) }}</div></div>
        <div class="card">
          <div class="text-sm text-muted">Pemasukan</div>
          <div class="text-lg font-bold text-ok md:text-xl">{{ rp(report.totals.iuran + report.totals.other_income) }}</div>
          <div class="text-xs text-muted">iuran {{ rp(report.totals.iuran) }}</div>
        </div>
        <div class="card"><div class="text-sm text-muted">Pengeluaran</div><div class="text-lg font-bold text-bad md:text-xl">{{ rp(report.totals.expense) }}</div></div>
        <div class="card border-primary! bg-primary-soft!">
          <div class="text-sm text-primary">Saldo kas</div>
          <div class="text-lg font-bold text-primary md:text-xl">{{ rp(report.closing_balance) }}</div>
        </div>
      </div>

      <div class="mb-4 grid gap-4 lg:grid-cols-[3fr_2fr]">
        <!-- Per bulan -->
        <section class="card">
          <h2 class="card-title">Arus kas per bulan</h2>
          <div class="list">
            <div v-for="m in months.slice().reverse()" :key="m.period" class="py-2.5">
              <div class="mb-1 flex items-baseline justify-between gap-2 text-sm">
                <b>{{ periodLabel(m.period, true) }}</b>
                <span class="text-muted">saldo <b class="text-ink">{{ rp(m.balance) }}</b></span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="w-10 text-muted">Masuk</span>
                <span class="h-2 rounded-full bg-ok" :style="{ width: `${((m.iuran + m.other_income) / maxBar) * 60}%` }" />
                <span class="text-ok">{{ rp(m.iuran + m.other_income) }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="w-10 text-muted">Keluar</span>
                <span class="h-2 rounded-full bg-bad" :style="{ width: `${(m.expense / maxBar) * 60}%` }" />
                <span class="text-bad">{{ rp(m.expense) }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Per kategori -->
        <section class="card self-start">
          <h2 class="card-title">Pengeluaran per kategori</h2>
          <p v-if="!report.expense_by_category.length" class="text-sm text-muted">Belum ada pengeluaran.</p>
          <div v-for="c in report.expense_by_category" :key="c.category" class="mb-2.5">
            <div class="flex justify-between text-sm"><span>{{ c.label }}</span><b>{{ rp(c.amount) }}</b></div>
            <div class="mt-1 h-2 rounded-full bg-surface-2">
              <div class="h-2 rounded-full bg-primary" :style="{ width: `${(c.amount / (report.totals.expense || 1)) * 100}%` }" />
            </div>
          </div>
        </section>
      </div>

      <!-- Transaksi -->
      <section class="card">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-[15px] font-semibold">Transaksi</h2>
          <div class="flex gap-2">
            <select v-model="month" class="input w-auto! py-1! text-sm!" aria-label="Bulan">
              <option value="">Semua bulan</option>
              <option v-for="m in months" :key="m.period" :value="Number(m.period.slice(5))">{{ monthShort(m.period) }}</option>
            </select>
            <select v-model="kind" class="input w-auto! py-1! text-sm!" aria-label="Jenis">
              <option value="">Semua</option>
              <option value="pemasukan">Pemasukan</option>
              <option value="pengeluaran">Pengeluaran</option>
            </select>
          </div>
        </div>
        <p class="mb-2 text-xs text-muted">Iuran warga tidak dicatat di sini; dihitung otomatis dari pembayaran iuran.</p>
        <p v-if="!entries.length" class="py-4 text-sm text-muted">Tidak ada transaksi.</p>
        <div class="list">
          <div v-for="e in entries" :key="e.id" class="flex items-center gap-3 py-2.5">
            <span
              class="grid size-9 flex-none place-items-center rounded-xl text-lg font-bold"
              :class="e.kind === 'pemasukan' ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'"
            >{{ e.kind === 'pemasukan' ? '+' : '−' }}</span>
            <div class="min-w-0 flex-1">
              <b class="block truncate">{{ e.description }}</b>
              <span class="text-sm text-muted">
                {{ dateLabel(e.date) }} · {{ e.category_label }}
                <a v-if="e.receipt_url" :href="e.receipt_url" target="_blank" rel="noopener" class="text-primary">· nota</a>
              </span>
            </div>
            <b class="whitespace-nowrap" :class="e.kind === 'pemasukan' ? 'text-ok' : 'text-bad'">{{ e.kind === 'pemasukan' ? '+' : '−' }}{{ rp(e.amount) }}</b>
            <template v-if="auth.isStaff">
              <button class="btn-icon" aria-label="Ubah" @click="openForm(e)"><AppIcon name="edit" :size="18" /></button>
              <button class="btn-icon" aria-label="Hapus" @click="remove(e)"><AppIcon name="x" :size="18" /></button>
            </template>
          </div>
        </div>
      </section>
    </template>
  </LoadState>

  <BaseModal :open="modal.open" :title="modal.entry ? 'Ubah transaksi kas' : 'Catat transaksi kas'" @close="modal = { open: false }">
    <form @submit.prevent="save">
      <div class="mb-4 flex gap-2">
        <button type="button" class="tab flex-1" :class="form.kind === 'pengeluaran' && 'tab-on'" @click="form.kind = 'pengeluaran'">Pengeluaran</button>
        <button type="button" class="tab flex-1" :class="form.kind === 'pemasukan' && 'tab-on'" @click="form.kind = 'pemasukan'">Pemasukan lain</button>
      </div>
      <label class="field"><span>Keterangan</span><input v-model="form.description" class="input" required maxlength="200" placeholder="mis. Honor petugas sampah" /></label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field">
          <span>Kategori</span>
          <select v-model="form.category" class="input"><option v-for="[k, l] in categories" :key="k" :value="k">{{ l }}</option></select>
        </label>
        <label class="field"><span>Tanggal</span><input v-model="form.date" class="input" type="date" required /></label>
      </div>
      <label class="field"><span>Jumlah (Rp)</span><input v-model.number="form.amount" class="input" type="number" min="1" required /></label>
      <label class="field">
        <span>Nota / kuitansi (opsional, JPG/PNG/PDF maks. 5 MB)</span>
        <input type="file" accept="image/*,application/pdf" class="input" @change="receipt = ($event.target as HTMLInputElement).files?.[0] ?? null" />
      </label>
      <p v-if="formError" class="mb-3 text-sm text-bad" role="alert">{{ formError }}</p>
      <button class="btn btn-primary w-full" :disabled="busy">{{ busy ? 'Menyimpan…' : 'Simpan' }}</button>
    </form>
  </BaseModal>
</template>
