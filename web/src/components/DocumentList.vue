<script setup lang="ts">
import { errMsg, http } from '@/api/http'
import type { ResidentDocument } from '@/api/types'
import { useToast } from '@/stores/toast'
import { dateLabel } from '@/utils/format'
import AppIcon from './AppIcon.vue'

/** Daftar dokumen KK/KTP. File privat dibuka lewat endpoint yang memeriksa hak akses. */
const props = defineProps<{ documents: ResidentDocument[]; canDelete?: boolean }>()
const emit = defineEmits<{ deleted: [] }>()
const toast = useToast()

async function remove(doc: ResidentDocument) {
  if (!confirm(`Hapus dokumen ${doc.kind_label}${doc.resident_name ? ` (${doc.resident_name})` : ''}? File akan dihapus permanen.`)) return
  try {
    await http.delete(`/documents/${doc.id}/`)
    toast.ok('Dokumen dihapus')
    emit('deleted')
  } catch (e) {
    toast.error(errMsg(e))
  }
}
</script>

<template>
  <p v-if="!props.documents.length" class="text-sm text-muted">Belum ada dokumen.</p>
  <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
    <figure v-for="d in props.documents" :key="d.id" class="overflow-hidden rounded-xl border border-line">
      <a :href="d.file_url" target="_blank" rel="noopener" class="block aspect-[4/3] bg-surface-2">
        <img v-if="d.file_type === 'image'" :src="d.file_url" :alt="d.kind_label" class="size-full object-contain" loading="lazy" />
        <span v-else class="grid size-full place-items-center text-sm font-semibold text-primary">PDF · buka</span>
      </a>
      <figcaption class="flex items-start gap-1 p-2 text-xs">
        <span class="min-w-0 flex-1">
          <b class="block text-sm">{{ d.kind_label }}</b>
          <span class="block truncate text-muted">{{ d.resident_name || d.note }}</span>
          <span class="text-muted">{{ dateLabel(d.created_at) }}</span>
        </span>
        <button v-if="canDelete" class="btn-icon size-7!" aria-label="Hapus dokumen" @click="remove(d)"><AppIcon name="x" :size="16" /></button>
      </figcaption>
    </figure>
  </div>
</template>
