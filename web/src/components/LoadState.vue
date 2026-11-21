<script setup lang="ts">
defineProps<{ loading: boolean; error?: string; empty?: boolean; emptyText?: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="loading" class="py-10 text-center text-muted">Memuat…</div>
  <div v-else-if="error" class="card text-center">
    <p class="mb-3 text-bad">{{ error }}</p>
    <button class="btn btn-sm" @click="$emit('retry')">Coba lagi</button>
  </div>
  <div v-else-if="empty" class="py-10 text-center text-muted">{{ emptyText ?? 'Belum ada data.' }}</div>
  <slot v-else />
</template>
