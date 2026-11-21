<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { RegisterMember } from '@/api/types'
import { GENDER, MARITAL, OCCUPANCY, RELATION, RELIGIONS, RESIDENCE, RESIDENCE_HINT } from '@/utils/labels'
import AppIcon from '@/components/AppIcon.vue'
import { compressImage } from '@/utils/image'

const step = ref(1)
const STEPS = ['Akun', 'Rumah', 'Keluarga', 'Kirim']
const error = ref('')
const busy = ref(false)
const done = ref(false)

const account = reactive({ username: '', phone: '', email: '', password: '', confirm: '' })
const household = reactive({
  block: '', house_number: '', address: '', no_kk: '', occupancy: 'pemilik', residence_status: 'menetap', since: '',
})
const blankMember = (relation: string): RegisterMember => ({
  name: '', nik: '', gender: 'L', birth_place: '', birth_date: '', religion: '', marital_status: '', relation, occupation: '', phone: '',
})
const members = ref<RegisterMember[]>([blankMember('kepala_keluarga')])
const consent = ref(false)
const kkFile = ref<File | null>(null)
const ktpFile = ref<File | null>(null)
const kkPreview = ref('')
const ktpPreview = ref('')

async function pick(e: Event, target: 'kk' | 'ktp') {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  const file = await compressImage(f)
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Ukuran file maksimal 5 MB.'
    return
  }
  error.value = ''
  const url = file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
  if (target === 'kk') {
    kkFile.value = file
    kkPreview.value = url
  } else {
    ktpFile.value = file
    ktpPreview.value = url
  }
}

const RELATIONS_OTHER = computed(() => Object.entries(RELATION).filter(([k]) => k !== 'kepala_keluarga'))

function next() {
  error.value = ''
  if (step.value === 1) {
    if (account.password !== account.confirm) return (error.value = 'Konfirmasi kata sandi tidak sama.')
    if (account.password.length < 8) return (error.value = 'Kata sandi minimal 8 karakter.')
  }
  if (step.value === 2 && !kkFile.value) return (error.value = 'Unggah foto Kartu Keluarga.')
  if (step.value === 3 && !ktpFile.value) return (error.value = 'Unggah foto KTP Anda.')
  step.value++
  window.scrollTo(0, 0)
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await http.get('/auth/csrf/')
    const fd = new FormData()
    fd.append('data', JSON.stringify({
      username: account.username.trim(),
      phone: account.phone.trim(),
      email: account.email.trim(),
      password: account.password,
      consent: consent.value,
      household: { ...household, since: household.since || null },
      members: members.value.map((m) => ({ ...m, birth_date: m.birth_date || null })),
    }))
    if (kkFile.value) fd.append('kk_file', kkFile.value)
    if (ktpFile.value) fd.append('ktp_file', ktpFile.value)
    await http.post('/auth/register/', fd)
    done.value = true
  } catch (e) {
    error.value = errMsg(e, 'Pendaftaran gagal. Periksa kembali data Anda.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mx-auto min-h-dvh max-w-2xl px-4 py-6 md:py-10">
    <RouterLink to="/login" class="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"><AppIcon name="back" :size="18" /> Kembali ke halaman masuk</RouterLink>
    <h1 class="text-2xl font-bold">Daftar sebagai warga baru</h1>
    <p class="mb-5 text-muted">Isi data diri dan keluarga Anda. Akun bisa dipakai setelah diaktifkan oleh pengurus RT.</p>

    <div v-if="done" class="card text-center">
      <div class="mx-auto mb-3 grid size-14 place-items-center rounded-full bg-ok-soft text-ok"><AppIcon name="check" :size="30" /></div>
      <h2 class="mb-1 text-lg font-bold">Pendaftaran terkirim</h2>
      <p class="mb-4 text-muted">Pengurus RT akan memeriksa data Anda. Setelah diaktifkan, masuk dengan username <b>{{ account.username }}</b> atau no. HP Anda.</p>
      <RouterLink to="/login" class="btn btn-primary">Ke halaman masuk</RouterLink>
    </div>

    <template v-else>
      <!-- Penunjuk langkah -->
      <ol class="mb-5 flex gap-2">
        <li v-for="(s, i) in STEPS" :key="s" class="flex-1">
          <div class="mb-1 h-1.5 rounded-full" :class="i + 1 <= step ? 'bg-primary' : 'bg-line'" />
          <span class="text-xs" :class="i + 1 === step ? 'font-semibold text-primary' : 'text-muted'">{{ i + 1 }}. {{ s }}</span>
        </li>
      </ol>

      <!-- 1. Akun -->
      <form v-if="step === 1" class="card" @submit.prevent="next">
        <h2 class="card-title">Akun untuk masuk</h2>
        <label class="field"><span>Username *</span><input v-model="account.username" class="input" required autocapitalize="none" autocomplete="username" pattern="[\w.@+\-]{3,150}" title="Minimal 3 karakter, tanpa spasi" /></label>
        <div class="grid gap-x-3 md:grid-cols-2">
          <label class="field"><span>No. HP (WhatsApp) *</span><input v-model="account.phone" class="input" type="tel" required maxlength="20" /></label>
          <label class="field"><span>Email (opsional)</span><input v-model="account.email" class="input" type="email" /></label>
          <label class="field"><span>Kata sandi (min. 8 karakter) *</span><input v-model="account.password" class="input" type="password" required minlength="8" autocomplete="new-password" /></label>
          <label class="field"><span>Ulangi kata sandi *</span><input v-model="account.confirm" class="input" type="password" required autocomplete="new-password" /></label>
        </div>
        <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
        <button class="btn btn-primary w-full">Lanjut</button>
      </form>

      <!-- 2. Rumah -->
      <form v-else-if="step === 2" class="card" @submit.prevent="next">
        <h2 class="card-title">Rumah & Kartu Keluarga</h2>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span>Blok *</span><input v-model="household.block" class="input" required maxlength="10" /></label>
          <label class="field"><span>No. rumah *</span><input v-model="household.house_number" class="input" required maxlength="10" /></label>
        </div>
        <label class="field"><span>Alamat lengkap</span><input v-model="household.address" class="input" maxlength="200" /></label>
        <label class="field"><span>No. KK (16 digit)</span><input v-model="household.no_kk" class="input" inputmode="numeric" maxlength="16" pattern="\d{16}" /></label>
        <div class="grid gap-x-3 md:grid-cols-2">
          <label class="field">
            <span>Status hunian</span>
            <select v-model="household.occupancy" class="input"><option v-for="(l, k) in OCCUPANCY" :key="k" :value="k">{{ l }}</option></select>
          </label>
          <label class="field"><span>Mulai tinggal</span><input v-model="household.since" class="input" type="date" /></label>
        </div>
        <fieldset class="field">
          <span>Status rumah *</span>
          <div class="grid gap-2 md:grid-cols-2">
            <label
              v-for="(l, k) in RESIDENCE"
              :key="k"
              class="flex cursor-pointer gap-3 rounded-xl border px-3 py-2.5"
              :class="household.residence_status === k ? 'border-primary bg-primary-soft' : 'border-line'"
            >
              <input v-model="household.residence_status" type="radio" :value="k" class="accent-[var(--c-primary)]" />
              <span><b>{{ l }}</b><br /><span class="text-sm text-muted">{{ RESIDENCE_HINT[k] }}</span></span>
            </label>
          </div>
        </fieldset>
        <label class="field">
          <span>Foto / scan Kartu Keluarga *</span>
          <span class="flex cursor-pointer flex-col items-center gap-1 rounded-xl border-2 border-dashed border-line p-4 text-center text-sm text-muted hover:border-primary hover:text-primary">
            <img v-if="kkPreview" :src="kkPreview" alt="Pratinjau KK" class="mb-1 max-h-40 rounded-lg" />
            <AppIcon v-else name="upload" :size="24" />
            {{ kkFile ? kkFile.name : 'Ketuk untuk foto atau pilih file (JPG/PNG/PDF, maks. 5 MB)' }}
            <input type="file" accept="image/*,application/pdf" class="sr-only" @change="pick($event, 'kk')" />
          </span>
        </label>
        <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
        <div class="flex gap-2">
          <button type="button" class="btn flex-1" @click="step--">Kembali</button>
          <button class="btn btn-primary flex-[2]">Lanjut</button>
        </div>
      </form>

      <!-- 3. Anggota keluarga -->
      <form v-else-if="step === 3" @submit.prevent="next">
        <section v-for="(m, i) in members" :key="i" class="card mb-3">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold">{{ i === 0 ? 'Data diri Anda' : `Anggota keluarga ${i + 1}` }}</h2>
            <button v-if="i > 0" type="button" class="btn-icon" aria-label="Hapus anggota" @click="members.splice(i, 1)"><AppIcon name="x" :size="18" /></button>
          </div>
          <div class="grid gap-x-3 md:grid-cols-2">
            <label class="field"><span>Nama lengkap *</span><input v-model="m.name" class="input" required maxlength="100" /></label>
            <label class="field"><span>NIK (16 digit)</span><input v-model="m.nik" class="input" inputmode="numeric" maxlength="16" pattern="\d{16}" /></label>
            <label class="field">
              <span>Hubungan dalam keluarga</span>
              <select v-model="m.relation" class="input">
                <option v-if="i === 0" value="kepala_keluarga">Kepala Keluarga</option>
                <option v-for="[k, l] in RELATIONS_OTHER" :key="k" :value="k">{{ l }}</option>
              </select>
            </label>
            <label class="field">
              <span>Jenis kelamin</span>
              <select v-model="m.gender" class="input"><option v-for="(l, k) in GENDER" :key="k" :value="k">{{ l }}</option></select>
            </label>
            <label class="field"><span>Tempat lahir</span><input v-model="m.birth_place" class="input" maxlength="60" /></label>
            <label class="field"><span>Tanggal lahir</span><input v-model="m.birth_date" class="input" type="date" /></label>
            <label class="field">
              <span>Agama</span>
              <select v-model="m.religion" class="input"><option value="">—</option><option v-for="x in RELIGIONS" :key="x">{{ x }}</option></select>
            </label>
            <label class="field">
              <span>Status perkawinan</span>
              <select v-model="m.marital_status" class="input"><option value="">—</option><option v-for="x in MARITAL" :key="x">{{ x }}</option></select>
            </label>
            <label class="field"><span>Pekerjaan</span><input v-model="m.occupation" class="input" maxlength="60" /></label>
            <label class="field"><span>No. HP</span><input v-model="m.phone" class="input" type="tel" maxlength="20" /></label>
          </div>
          <label v-if="i === 0" class="field">
            <span>Foto KTP Anda *</span>
            <span class="flex cursor-pointer flex-col items-center gap-1 rounded-xl border-2 border-dashed border-line p-4 text-center text-sm text-muted hover:border-primary hover:text-primary">
              <img v-if="ktpPreview" :src="ktpPreview" alt="Pratinjau KTP" class="mb-1 max-h-32 rounded-lg" />
              <AppIcon v-else name="upload" :size="24" />
              {{ ktpFile ? ktpFile.name : 'Ketuk untuk foto atau pilih file' }}
              <input type="file" accept="image/*,application/pdf" class="sr-only" @change="pick($event, 'ktp')" />
            </span>
          </label>
        </section>
        <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
        <button v-if="members.length < 15" type="button" class="btn mb-4 w-full" @click="members.push(blankMember('anak'))">
          <AppIcon name="plus" :size="18" />Tambah anggota keluarga
        </button>
        <div class="flex gap-2">
          <button type="button" class="btn flex-1" @click="step--">Kembali</button>
          <button class="btn btn-primary flex-[2]">Lanjut</button>
        </div>
      </form>

      <!-- 4. Ringkasan -->
      <form v-else class="card" @submit.prevent="submit">
        <h2 class="card-title">Periksa & kirim</h2>
        <dl class="list mb-4 text-sm">
          <div class="flex justify-between gap-4 py-2"><dt class="text-muted">Username</dt><dd class="font-semibold">{{ account.username }}</dd></div>
          <div class="flex justify-between gap-4 py-2"><dt class="text-muted">No. HP</dt><dd class="font-semibold">{{ account.phone }}</dd></div>
          <div class="flex justify-between gap-4 py-2">
            <dt class="text-muted">Rumah</dt>
            <dd class="text-right font-semibold">{{ household.block }}-{{ household.house_number }} · {{ OCCUPANCY[household.occupancy] }} · {{ RESIDENCE[household.residence_status] }}</dd>
          </div>
          <div class="flex justify-between gap-4 py-2">
            <dt class="text-muted">Anggota keluarga</dt>
            <dd class="text-right font-semibold">{{ members.map((m) => m.name).join(', ') }}</dd>
          </div>
          <div class="flex justify-between gap-4 py-2"><dt class="text-muted">Dokumen</dt><dd class="font-semibold">KK ✓ · KTP ✓</dd></div>
        </dl>
        <label class="mb-4 flex gap-3 rounded-xl bg-surface-2 p-3 text-sm">
          <input v-model="consent" type="checkbox" required class="mt-0.5 accent-[var(--c-primary)]" />
          <span>Saya menyatakan data di atas benar dan menyetujui data serta foto KK/KTP ini disimpan dan digunakan oleh pengurus RT hanya untuk keperluan administrasi warga.</span>
        </label>
        <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
        <div class="flex gap-2">
          <button type="button" class="btn flex-1" @click="step--">Kembali</button>
          <button class="btn btn-primary flex-[2]" :disabled="busy || !consent">{{ busy ? 'Mengirim…' : 'Kirim pendaftaran' }}</button>
        </div>
      </form>
    </template>
  </div>
</template>
