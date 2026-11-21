import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  text: string
  kind: 'ok' | 'error'
}

export const useToast = defineStore('toast', () => {
  const items = ref<Toast[]>([])
  let seq = 0

  function show(text: string, kind: Toast['kind'] = 'ok') {
    const id = ++seq
    items.value.push({ id, text, kind })
    setTimeout(() => (items.value = items.value.filter((t) => t.id !== id)), kind === 'error' ? 5000 : 3000)
  }

  return { items, show, ok: (t: string) => show(t, 'ok'), error: (t: string) => show(t, 'error') }
})
