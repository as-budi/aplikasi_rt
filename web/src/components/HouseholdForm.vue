<script setup lang="ts">
import { reactive, ref } from 'vue'
import { errMsg, http } from '@/api/http'
import type { HouseholdWrite } from '@/api/types'
import { OCCUPANCY, RESIDENCE, RESIDENCE_HINT } from '@/utils/labels'

const props = defineProps<{ initial?: HouseholdWrite }>()
const emit = defineEmits<{ saved: [id: number] }>()

const form = reactive<HouseholdWrite>({
  no_kk: props.initial?.no_kk ?? '',
  block: props.initial?.block ?? '',
  house_number: props.initial?.house_number ?? '',
  address: props.initial?.address ?? '',
  occupancy: props.initial?.occupancy ?? 'pemilik',
  residence_status: props.initial?.residence_status ?? 'menetap',
  since: props.initial?.since ?? null,
})
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const payload = { ...form, since: form.since || null }
    const { data } = props.initial?.id
      ? await http.patch<HouseholdWrite>(`/households/${props.initial.id}/`, payload)
      : await http.post<HouseholdWrite>('/households/', payload)
    emit('saved', data.id as number)
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form @submit.prevent="submit">
    <label class="field">
      <span>No. KK (16 digit)</span>
      <input v-model="form.no_kk" class="input" inputmode="numeric" maxlength="16" pattern="\d{16}" />
    </label>
    <div class="grid grid-cols-2 gap-3">
      <label class="field"><span>Blok *</span><input v-model="form.block" class="input" required maxlength="10" /></label>
      <label class="field"><span>No. rumah *</span><input v-model="form.house_number" class="input" required maxlength="10" /></label>
    </div>
    <label class="field"><span>Alamat lengkap</span><input v-model="form.address" class="input" maxlength="200" /></label>
    <div class="grid grid-cols-2 gap-3">
      <label class="field">
        <span>Status hunian</span>
        <select v-model="form.occupancy" class="input">
          <option v-for="(label, key) in OCCUPANCY" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label class="field">
        <span>Status rumah</span>
        <select v-model="form.residence_status" class="input">
          <option v-for="(label, key) in RESIDENCE" :key="key" :value="key">{{ label }} — {{ RESIDENCE_HINT[key] }}</option>
        </select>
      </label>
    </div>
    <label class="field"><span>Tinggal sejak</span><input v-model="form.since" class="input" type="date" /></label>
    <p v-if="error" class="mb-3 text-sm text-bad" role="alert">{{ error }}</p>
    <button class="btn btn-primary w-full" :disabled="busy">{{ busy ? 'Menyimpan…' : 'Simpan' }}</button>
  </form>
</template>
