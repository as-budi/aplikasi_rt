<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

/** Tombol unduh Excel/PDF. Unduhan memakai link biasa: cookie sesi ikut terkirim. */
const props = defineProps<{ kind: 'residents' | 'dues' | 'cash'; year?: number }>()

const url = (file: 'xlsx' | 'pdf') =>
  computed(() => `/api/v1/exports/${props.kind}/?file=${file}${props.year ? `&year=${props.year}` : ''}`)
const xlsx = url('xlsx')
const pdf = url('pdf')
</script>

<template>
  <div class="flex gap-2">
    <a :href="xlsx" class="btn btn-sm" download><AppIcon name="download" :size="16" />Excel</a>
    <a :href="pdf" class="btn btn-sm" download><AppIcon name="download" :size="16" />PDF</a>
  </div>
</template>
