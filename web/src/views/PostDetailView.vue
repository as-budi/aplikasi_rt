<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errMsg, http } from '@/api/http'
import type { Post } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import { dateLabel, dateTimeLabel } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import LoadState from '@/components/LoadState.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const post = ref<Post | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    post.value = (await http.get<Post>(`/posts/${route.params.id}/`)).data
  } catch (e) {
    error.value = errMsg(e, 'Posting tidak ditemukan.')
  } finally {
    loading.value = false
  }
}

async function remove() {
  if (!post.value || !confirm('Hapus posting ini?')) return
  try {
    await http.delete(`/posts/${post.value.id}/`)
    toast.ok('Posting dihapus')
    router.replace('/berita')
  } catch (e) {
    toast.error(errMsg(e))
  }
}

onMounted(load)
</script>

<template>
  <RouterLink to="/berita" class="mb-3 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"><AppIcon name="back" :size="18" /> Semua berita</RouterLink>
  <LoadState :loading="loading" :error="error" @retry="load">
    <article v-if="post" class="card max-w-3xl">
      <div class="mb-2 flex flex-wrap gap-1.5">
        <span class="badge" :class="post.type === 'kegiatan' ? 'badge-primary' : 'badge-warn'">{{ post.type === 'kegiatan' ? 'Kegiatan' : 'Berita' }}</span>
        <span v-if="!post.is_published" class="badge badge-muted">Draf</span>
      </div>
      <h2 class="mb-2 text-xl font-bold md:text-2xl">{{ post.title }}</h2>
      <p class="mb-4 text-sm text-muted">{{ post.author_name }} · {{ dateLabel(post.published_at ?? post.created_at) }}</p>
      <div v-if="post.type === 'kegiatan'" class="mb-4 grid gap-2 rounded-xl bg-primary-soft p-3 text-sm text-primary">
        <span class="flex items-center gap-2"><AppIcon name="calendar" :size="18" />{{ dateTimeLabel(post.event_at) }}</span>
        <span v-if="post.location" class="flex items-center gap-2"><AppIcon name="pin" :size="18" />{{ post.location }}</span>
      </div>
      <div class="whitespace-pre-line leading-relaxed">{{ post.body }}</div>
      <div v-if="auth.isStaff" class="mt-6 flex gap-2 border-t border-line pt-4">
        <RouterLink :to="`/berita/${post.id}/ubah`" class="btn btn-sm"><AppIcon name="edit" :size="16" />Ubah</RouterLink>
        <button class="btn btn-sm btn-danger" @click="remove">Hapus</button>
      </div>
    </article>
  </LoadState>
</template>
