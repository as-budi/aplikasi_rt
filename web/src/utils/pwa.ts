import { ref } from 'vue'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/** Event "pasang aplikasi" dari Chrome/Android, disimpan agar bisa dipicu dari tombol. */
export const installEvent = ref<BeforeInstallPromptEvent | null>(null)

export const isStandalone = () =>
  window.matchMedia('(display-mode: standalone)').matches || (navigator as { standalone?: boolean }).standalone === true

export function listenInstallPrompt() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    installEvent.value = e as BeforeInstallPromptEvent
  })
  window.addEventListener('appinstalled', () => (installEvent.value = null))
}

export async function promptInstall() {
  const ev = installEvent.value
  if (!ev) return
  await ev.prompt()
  await ev.userChoice
  installEvent.value = null
}
