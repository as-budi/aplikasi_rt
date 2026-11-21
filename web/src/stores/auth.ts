import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { http } from '@/api/http'
import type { Me } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<Me | null>(null)
  const loaded = ref(false)

  const isStaff = computed(() => !!user.value?.is_staff_rt)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function fetchMe() {
    try {
      await http.get('/auth/csrf/')
      const { data } = await http.get<Me>('/auth/me/')
      user.value = data
    } catch {
      user.value = null
    } finally {
      loaded.value = true
    }
  }

  async function login(identifier: string, password: string) {
    await http.get('/auth/csrf/')
    const { data } = await http.post<Me>('/auth/login/', { identifier, password })
    user.value = data
  }

  async function logout() {
    try {
      await http.post('/auth/logout/')
    } finally {
      user.value = null
      // Jangan tinggalkan data warga di cache perangkat (HP bisa dipakai bersama)
      if ('caches' in window) await caches.delete('api')
    }
  }

  return { user, loaded, isStaff, isAdmin, fetchMe, login, logout }
})
