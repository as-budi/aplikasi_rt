<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errMsg } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const identifier = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.login(identifier.value.trim(), password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/'
    await router.replace(next)
  } catch (e) {
    error.value = errMsg(e, 'Gagal masuk. Coba lagi.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="grid min-h-dvh place-items-center px-4 py-10">
    <div class="w-full max-w-sm">
      <div class="mb-8 text-center">
        <div class="mx-auto mb-4 grid size-16 place-items-center rounded-2xl bg-primary text-2xl font-extrabold text-on-primary">RT</div>
        <h1 class="text-2xl font-bold">RT Kita</h1>
        <p class="text-muted">Administrasi warga, iuran, dan kegiatan</p>
      </div>
      <form class="card" @submit.prevent="submit">
        <label class="field">
          <span>Username atau No. HP</span>
          <input v-model="identifier" class="input" autocomplete="username" autocapitalize="none" required autofocus />
        </label>
        <label class="field">
          <span>Kata sandi</span>
          <input v-model="password" class="input" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="mb-3 rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad" role="alert">{{ error }}</p>
        <button class="btn btn-primary w-full py-2.5" :disabled="busy">{{ busy ? 'Memproses…' : 'Masuk' }}</button>
      </form>
      <RouterLink to="/daftar" class="btn mt-4 w-full">Daftar sebagai warga baru</RouterLink>
      <p class="mt-4 text-center text-sm text-muted">Lupa kata sandi? Hubungi pengurus RT.</p>
    </div>
  </div>
</template>
