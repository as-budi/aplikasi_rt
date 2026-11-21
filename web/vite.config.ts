import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// Di pengembangan, API Django ada di service `api` (Docker). Di luar Docker: API_URL=http://localhost:8000
const API_URL = process.env.API_URL ?? 'http://api:8000'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'RT Kita — Administrasi RT',
        short_name: 'RT Kita',
        description: 'Data warga, iuran, dan berita RT',
        lang: 'id',
        theme_color: '#0f766e',
        background_color: '#f4f6f5',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/admin/, /^\/static\//],
        runtimeCaching: [
          {
            // Data terakhir tetap bisa dibaca saat sinyal hilang (bukan file bukti bayar)
            urlPattern: ({ url, request }) =>
              url.pathname.startsWith('/api/v1/') && request.method === 'GET' && !url.pathname.endsWith('/file/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api',
              networkTimeoutSeconds: 6,
              expiration: { maxEntries: 150, maxAgeSeconds: 60 * 60 * 24 * 3 },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': API_URL,
      '/admin': API_URL,
      '/static': API_URL,
    },
  },
})
