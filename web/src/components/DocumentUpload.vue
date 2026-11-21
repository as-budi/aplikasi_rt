<script setup lang="ts">
import { ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { Resident } from '@/api/types'
import { compressImage } from '@/utils/image'

/** Unggah KK/KTP. `householdId` diisi oleh pengurus; warga otomatis ke KK sendiri. */
const props = defineProps<{ householdId?: number; members: Resident[] }>()
const emit = defineEmits<{ uploaded: [] }>()

const kind = ref<'kk' | 'ktp' | 'lainnya'>('kk')
const resident = ref<number | ''>('')
const note = ref('')
const file = ref<File | null>(null)
const error = ref('')
const busy = ref(false)

async function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  file.value = f ? await compressImage(f) : null
}

async function submit() {
  if (!file.value) return (error.value = 'Pilih foto atau file dokumen.')
  if (kind.value === 'ktp' && !resident.value) return (error.value = 'Pilih pemilik KTP.')
  busy.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('kind', kind.value)
    fd.append('file', file.value)
    fd.append('note', note.value)
    if (resident.value) fd.append('resident', String(resident.value))
    if (props.householdId) fd.append('household', String(props.householdId))
    await http.post('/documents/', fd)
    emit('uploaded')
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form @submit.prevent="submit">
    <div class="grid grid-cols-2 gap-3">
      <label class="field">
        <span>Jenis dokumen</span>
        <select v-model="kind" class="input">
          <option value="kk">Kartu Keluarga</option>
          <option value="ktp">KTP</option>
          <option value="lainnya">Lainnya</option>
        </select>
      </label>
      <label class="field">
        <span>Milik {{ kind === 'ktp' ? '*' : '(opsional)' }}</span>
        <select v-model="resident" class="input">
          <option value="">—</option>
          <option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
      </label>
    </div>
    <label class="field"><span>Keterangan (opsional)</span><input v-model="note" class="input" maxlength="150" placeholder="mis. KK terbaru 2026" /></label>
    <label class="field">
      <span>Foto / scan (JPG, PNG, PDF · maks. 5 MB)</span>
      <input type="file" accept="image/*,application/pdf" class="input" required @change="onFile" />
    </label>
    <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
    <button class="btn btn-primary w-full" :disabled="busy">{{ busy ? 'Mengunggah…' : 'Unggah dokumen' }}</button>
  </form>
</template>
