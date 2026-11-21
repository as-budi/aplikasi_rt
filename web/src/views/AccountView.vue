<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errMsg, http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import { initials } from '@/utils/format'
import { ROLE } from '@/utils/labels'
import { installEvent, isStandalone, promptInstall } from '@/utils/pwa'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const pw = reactive({ old_password: '', new_password: '', confirm: '' })
const pwError = ref('')
const busy = ref(false)
const standalone = isStandalone()

async function changePassword() {
  pwError.value = ''
  if (pw.new_password !== pw.confirm) return (pwError.value = 'Konfirmasi kata sandi tidak sama.')
  busy.value = true
  try {
    await http.post('/auth/password/', { old_password: pw.old_password, new_password: pw.new_password })
    Object.assign(pw, { old_password: '', new_password: '', confirm: '' })
    toast.ok('Kata sandi berhasil diubah')
  } catch (e) {
    pwError.value = errMsg(e)
  } finally {
    busy.value = false
  }
}

async function logout() {
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="grid max-w-3xl gap-4">
    <section v-if="auth.user" class="card flex items-center gap-4">
      <span class="avatar size-14! text-lg!">{{ initials(auth.user.name) }}</span>
      <div class="min-w-0 flex-1">
        <div class="text-lg font-bold">{{ auth.user.name }}</div>
        <div class="text-sm text-muted">
          @{{ auth.user.username }} · {{ ROLE[auth.user.role] }}<template v-if="auth.user.household_label"> · Rumah {{ auth.user.household_label }}</template>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="list">
        <RouterLink to="/saya" class="flex items-center gap-3 py-3"><AppIcon name="idcard" /> <span class="flex-1">Data keluarga saya</span><AppIcon name="chevron" class="text-muted" /></RouterLink>
        <RouterLink v-if="auth.isStaff" to="/pengajuan" class="flex items-center gap-3 py-3"><AppIcon name="inbox" /> <span class="flex-1">Pengajuan perubahan data</span><AppIcon name="chevron" class="text-muted" /></RouterLink>
        <a v-if="auth.isAdmin" href="/admin/" class="flex items-center gap-3 py-3"><AppIcon name="settings" /> <span class="flex-1">Pengaturan (Django Admin): pengguna, jenis iuran, log</span><AppIcon name="chevron" class="text-muted" /></a>
      </div>
    </section>

    <section v-if="!standalone" class="card">
      <h2 class="card-title">Pasang aplikasi di HP</h2>
      <button v-if="installEvent" class="btn btn-primary" @click="promptInstall"><AppIcon name="download" :size="18" />Pasang RT Kita</button>
      <p v-else class="text-sm text-muted">
        <b>Android (Chrome):</b> menu ⋮ → <i>Tambahkan ke layar utama</i>.<br />
        <b>iPhone (Safari):</b> tombol Bagikan → <i>Tambah ke Layar Utama</i>.
      </p>
    </section>

    <form class="card" @submit.prevent="changePassword">
      <h2 class="card-title">Ganti kata sandi</h2>
      <label class="field"><span>Kata sandi lama</span><input v-model="pw.old_password" class="input" type="password" autocomplete="current-password" required /></label>
      <div class="grid gap-x-3 md:grid-cols-2">
        <label class="field"><span>Kata sandi baru (min. 8 karakter)</span><input v-model="pw.new_password" class="input" type="password" autocomplete="new-password" minlength="8" required /></label>
        <label class="field"><span>Ulangi kata sandi baru</span><input v-model="pw.confirm" class="input" type="password" autocomplete="new-password" required /></label>
      </div>
      <p v-if="pwError" class="mb-3 text-sm text-bad" role="alert">{{ pwError }}</p>
      <button class="btn btn-primary" :disabled="busy">Simpan kata sandi</button>
    </form>

    <button class="btn btn-danger" @click="logout"><AppIcon name="logout" :size="18" />Keluar</button>
  </div>
</template>
