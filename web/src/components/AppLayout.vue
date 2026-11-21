<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ROLE } from '@/utils/labels'
import { initials } from '@/utils/format'
import AppIcon from './AppIcon.vue'

const auth = useAuthStore()
const route = useRoute()

interface NavItem {
  to: string
  label: string
  short?: string
  icon: string
  mobile: boolean
}

const items = computed<NavItem[]>(() => {
  const staff = auth.isStaff
  const list: NavItem[] = [{ to: '/', label: 'Beranda', icon: 'home', mobile: true }]
  if (staff) list.push({ to: '/warga', label: 'Data Warga', short: 'Warga', icon: 'users', mobile: true })
  list.push({ to: '/saya', label: 'Data Saya', icon: 'idcard', mobile: !staff })
  if (staff) list.push({ to: '/pengajuan', label: 'Pengajuan Data', icon: 'inbox', mobile: false })
  if (staff) list.push({ to: '/pendaftaran', label: 'Pendaftaran Baru', icon: 'userplus', mobile: false })
  list.push({ to: '/iuran', label: 'Iuran', icon: 'wallet', mobile: true })
  list.push({ to: '/kas', label: 'Kas RT', icon: 'cash', mobile: false })
  list.push({ to: '/berita', label: 'Berita & Kegiatan', short: 'Berita', icon: 'news', mobile: true })
  list.push({ to: '/akun', label: 'Akun', icon: 'user', mobile: true })
  return list
})

const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>

<template>
  <div class="min-h-dvh md:flex">
    <!-- Sidebar: tablet & desktop -->
    <aside class="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-line bg-surface p-4 md:flex">
      <RouterLink to="/" class="mb-5 flex items-center gap-2.5 px-2 text-[17px] font-bold">
        <span class="grid size-9 place-items-center rounded-[10px] bg-primary text-sm font-extrabold text-on-primary">RT</span>
        RT Kita
      </RouterLink>
      <nav class="flex flex-col gap-1">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-muted hover:bg-surface-2 hover:text-ink"
          :class="isActive(item.to) && 'bg-primary-soft! font-semibold text-primary!'"
        >
          <AppIcon :name="item.icon" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="flex-1" />
      <div v-if="auth.user" class="flex items-center gap-3 rounded-xl bg-surface-2 p-3">
        <span class="avatar">{{ initials(auth.user.name) }}</span>
        <div class="min-w-0 text-sm">
          <div class="truncate font-semibold">{{ auth.user.name }}</div>
          <div class="text-muted">{{ ROLE[auth.user.role] }}<template v-if="auth.user.household_label"> · {{ auth.user.household_label }}</template></div>
        </div>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="sticky top-0 z-10 border-b border-line bg-surface/95 pt-[env(safe-area-inset-top)] backdrop-blur">
        <div class="flex h-14 items-center gap-3 px-4 md:px-7">
          <span class="grid size-8 place-items-center rounded-[9px] bg-primary text-xs font-extrabold text-on-primary md:hidden">RT</span>
          <h1 class="flex-1 truncate text-[17px] font-semibold md:text-lg">{{ route.meta.title }}</h1>
        </div>
      </header>
      <main class="w-full max-w-6xl flex-1 px-4 pt-4 pb-28 md:px-7 md:pt-6 md:pb-10">
        <RouterView />
      </main>
    </div>

    <!-- Navigasi bawah: HP -->
    <nav class="fixed inset-x-0 bottom-0 z-20 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden">
      <RouterLink
        v-for="item in items.filter((i) => i.mobile)"
        :key="item.to"
        :to="item.to"
        class="flex flex-1 flex-col items-center gap-0.5 pt-2 pb-1.5 text-[11px] text-muted"
        :class="isActive(item.to) && 'font-semibold text-primary!'"
      >
        <span class="grid h-7 w-14 place-items-center rounded-full" :class="isActive(item.to) && 'bg-primary-soft'">
          <AppIcon :name="item.icon" :size="21" />
        </span>
        {{ item.short ?? item.label }}
      </RouterLink>
    </nav>
  </div>
</template>
