<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errMsg, http } from '@/api/http'
import type { Post, PostType } from '@/api/types'
import { useToast } from '@/stores/toast'
import { toLocalInput } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const id = route.params.id ? Number(route.params.id) : null

const form = reactive({
  type: 'berita' as PostType,
  title: '',
  body: '',
  event_at: '',
  location: '',
  is_pinned: false,
  is_published: true,
})
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  if (!id) return
  try {
    const p = (await http.get<Post>(`/posts/${id}/`)).data
    Object.assign(form, { ...p, event_at: toLocalInput(p.event_at) })
  } catch (e) {
    error.value = errMsg(e)
  }
})

async function save(publish: boolean) {
  busy.value = true
  error.value = ''
  try {
    const payload = {
      type: form.type,
      title: form.title,
      body: form.body,
      event_at: form.type === 'kegiatan' && form.event_at ? form.event_at : null,
      location: form.type === 'kegiatan' ? form.location : '',
      is_pinned: form.is_pinned,
      is_published: publish,
    }
    const { data } = id ? await http.patch<Post>(`/posts/${id}/`, payload) : await http.post<Post>('/posts/', payload)
    toast.ok(publish ? 'Posting diterbitkan' : 'Draf disimpan')
    router.replace(`/berita/${data.id}`)
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="card max-w-2xl" @submit.prevent="save(true)">
    <div class="mb-4 flex gap-2">
      <button type="button" class="tab" :class="form.type === 'berita' && 'tab-on'" @click="form.type = 'berita'">Berita / pengumuman</button>
      <button type="button" class="tab" :class="form.type === 'kegiatan' && 'tab-on'" @click="form.type = 'kegiatan'">Kegiatan</button>
    </div>
    <label class="field"><span>Judul</span><input v-model="form.title" class="input" required maxlength="150" /></label>
    <div v-if="form.type === 'kegiatan'" class="grid gap-x-3 md:grid-cols-2">
      <label class="field"><span>Tanggal & jam</span><input v-model="form.event_at" class="input" type="datetime-local" required /></label>
      <label class="field"><span>Lokasi</span><input v-model="form.location" class="input" maxlength="150" /></label>
    </div>
    <label class="field"><span>Isi</span><textarea v-model="form.body" class="input" rows="8" required /></label>
    <label class="mb-4 flex items-center gap-2 text-sm"><input v-model="form.is_pinned" type="checkbox" /> Sematkan di paling atas</label>
    <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
    <div class="flex gap-2">
      <button type="button" class="btn flex-1" :disabled="busy" @click="save(false)">Simpan draf</button>
      <button class="btn btn-primary flex-[2]" :disabled="busy">{{ form.is_published && id ? 'Simpan' : 'Terbitkan' }}</button>
    </div>
  </form>
</template>
