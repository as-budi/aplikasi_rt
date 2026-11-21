<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { errMsg, http } from '@/api/http'
import type { Paginated, Post, PostType } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { dateLabel, dateTimeLabel } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import LoadState from '@/components/LoadState.vue'

const auth = useAuthStore()
const type = ref<PostType | ''>('')
const posts = ref<Post[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    posts.value = (await http.get<Paginated<Post>>('/posts/', { params: { type: type.value || undefined, page_size: 50 } })).data.results
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

watch(type, load)
onMounted(load)
</script>

<template>
  <div class="mb-4 flex items-center justify-between gap-2">
    <div class="no-scrollbar flex gap-2 overflow-x-auto">
      <button class="tab" :class="type === '' && 'tab-on'" @click="type = ''">Semua</button>
      <button class="tab" :class="type === 'berita' && 'tab-on'" @click="type = 'berita'">Berita</button>
      <button class="tab" :class="type === 'kegiatan' && 'tab-on'" @click="type = 'kegiatan'">Kegiatan</button>
    </div>
    <RouterLink v-if="auth.isStaff" to="/berita/baru" class="btn btn-primary hidden md:inline-flex"><AppIcon name="plus" :size="18" />Buat posting</RouterLink>
  </div>

  <LoadState :loading="loading" :error="error" :empty="!posts.length" empty-text="Belum ada posting." @retry="load">
    <div class="grid gap-3 md:grid-cols-2">
      <RouterLink v-for="p in posts" :key="p.id" :to="`/berita/${p.id}`" class="card flex gap-3 hover:bg-surface-2">
        <span
          class="grid size-14 flex-none place-items-center rounded-xl md:size-16"
          :class="p.type === 'kegiatan' ? 'bg-primary-soft text-primary' : 'bg-warn-soft text-warn'"
        >
          <AppIcon :name="p.type === 'kegiatan' ? 'calendar' : 'news'" :size="26" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="mb-1 flex flex-wrap items-center gap-1.5">
            <span class="badge" :class="p.type === 'kegiatan' ? 'badge-primary' : 'badge-warn'">{{ p.type === 'kegiatan' ? 'Kegiatan' : 'Berita' }}</span>
            <span v-if="p.is_pinned" class="badge badge-muted">Disematkan</span>
            <span v-if="!p.is_published" class="badge badge-muted">Draf</span>
          </span>
          <b class="block">{{ p.title }}</b>
          <span class="block text-sm text-muted">
            <template v-if="p.type === 'kegiatan'">{{ dateTimeLabel(p.event_at) }}<template v-if="p.location"> · {{ p.location }}</template></template>
            <template v-else>{{ dateLabel(p.published_at ?? p.created_at) }}</template>
          </span>
          <span class="mt-1 line-clamp-2 hidden text-sm md:block">{{ p.body }}</span>
        </span>
      </RouterLink>
    </div>
  </LoadState>

  <RouterLink
    v-if="auth.isStaff"
    to="/berita/baru"
    class="fixed right-4 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-10 grid size-14 place-items-center rounded-2xl bg-primary text-on-primary shadow-lg md:hidden"
    aria-label="Buat posting"
  >
    <AppIcon name="plus" :size="26" />
  </RouterLink>
</template>
