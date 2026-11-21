<script setup lang="ts">
import { reactive, ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { Resident } from '@/api/types'
import { GENDER, MARITAL, RELATION, RELIGIONS, RESIDENT_STATUS } from '@/utils/labels'

const props = defineProps<{ householdId: number; resident?: Resident }>()
const emit = defineEmits<{ saved: [] }>()

const r = props.resident
const form = reactive({
  name: r?.name ?? '',
  nik: r?.nik ?? '',
  gender: r?.gender ?? 'L',
  relation: r?.relation ?? 'anak',
  birth_place: r?.birth_place ?? '',
  birth_date: r?.birth_date ?? '',
  religion: r?.religion ?? '',
  marital_status: r?.marital_status ?? '',
  occupation: r?.occupation ?? '',
  phone: r?.phone ?? '',
  status: r?.status ?? 'aktif',
})
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const payload = { ...form, birth_date: form.birth_date || null, household: props.householdId }
    if (r) await http.patch(`/residents/${r.id}/`, payload)
    else await http.post('/residents/', payload)
    emit('saved')
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form @submit.prevent="submit">
    <label class="field"><span>Nama lengkap *</span><input v-model="form.name" class="input" required maxlength="100" /></label>
    <label class="field"><span>NIK (16 digit)</span><input v-model="form.nik" class="input" inputmode="numeric" maxlength="16" pattern="\d{16}" /></label>
    <div class="grid grid-cols-2 gap-3">
      <label class="field">
        <span>Jenis kelamin</span>
        <select v-model="form.gender" class="input"><option v-for="(l, k) in GENDER" :key="k" :value="k">{{ l }}</option></select>
      </label>
      <label class="field">
        <span>Hubungan</span>
        <select v-model="form.relation" class="input"><option v-for="(l, k) in RELATION" :key="k" :value="k">{{ l }}</option></select>
      </label>
      <label class="field"><span>Tempat lahir</span><input v-model="form.birth_place" class="input" maxlength="60" /></label>
      <label class="field"><span>Tanggal lahir</span><input v-model="form.birth_date" class="input" type="date" /></label>
      <label class="field">
        <span>Agama</span>
        <select v-model="form.religion" class="input"><option value="">—</option><option v-for="x in RELIGIONS" :key="x">{{ x }}</option></select>
      </label>
      <label class="field">
        <span>Status perkawinan</span>
        <select v-model="form.marital_status" class="input"><option value="">—</option><option v-for="x in MARITAL" :key="x">{{ x }}</option></select>
      </label>
      <label class="field"><span>Pekerjaan</span><input v-model="form.occupation" class="input" maxlength="60" /></label>
      <label class="field"><span>No. HP</span><input v-model="form.phone" class="input" type="tel" maxlength="20" /></label>
    </div>
    <label v-if="r" class="field">
      <span>Status</span>
      <select v-model="form.status" class="input"><option v-for="(l, k) in RESIDENT_STATUS" :key="k" :value="k">{{ l }}</option></select>
    </label>
    <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
    <button class="btn btn-primary w-full" :disabled="busy">{{ busy ? 'Menyimpan…' : 'Simpan' }}</button>
  </form>
</template>
