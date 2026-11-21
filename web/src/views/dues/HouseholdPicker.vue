<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAll } from '@/api/http'
import type { HouseholdListItem } from '@/api/types'

defineProps<{ modelValue: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [id: number] }>()

const households = ref<HouseholdListItem[]>([])
onMounted(async () => {
  households.value = await fetchAll<HouseholdListItem>('/households/', { is_active: true })
})
</script>

<template>
  <select
    class="input"
    :value="modelValue ?? ''"
    @change="emit('update:modelValue', Number(($event.target as HTMLSelectElement).value))"
  >
    <option value="" disabled>Pilih KK…</option>
    <option v-for="h in households" :key="h.id" :value="h.id">{{ h.label }} · {{ h.head_name }}</option>
  </select>
</template>
