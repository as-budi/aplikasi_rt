import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    public?: boolean
    staff?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true, title: 'Masuk' } },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', component: () => import('@/views/HomeView.vue'), meta: { title: 'Beranda' } },
        { path: 'warga', component: () => import('@/views/HouseholdsView.vue'), meta: { title: 'Data Warga', staff: true } },
        { path: 'warga/:id', component: () => import('@/views/HouseholdDetailView.vue'), meta: { title: 'Detail Keluarga', staff: true } },
        { path: 'saya', component: () => import('@/views/MyDataView.vue'), meta: { title: 'Data Saya' } },
        { path: 'pengajuan', component: () => import('@/views/ChangeRequestsView.vue'), meta: { title: 'Pengajuan Perubahan', staff: true } },
        { path: 'iuran', component: () => import('@/views/DuesView.vue'), meta: { title: 'Iuran' } },
        { path: 'berita', component: () => import('@/views/PostsView.vue'), meta: { title: 'Berita & Kegiatan' } },
        { path: 'berita/baru', component: () => import('@/views/PostFormView.vue'), meta: { title: 'Buat Posting', staff: true } },
        { path: 'berita/:id', component: () => import('@/views/PostDetailView.vue'), meta: { title: 'Berita & Kegiatan' } },
        { path: 'berita/:id/ubah', component: () => import('@/views/PostFormView.vue'), meta: { title: 'Ubah Posting', staff: true } },
        { path: 'akun', component: () => import('@/views/AccountView.vue'), meta: { title: 'Akun' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loaded) await auth.fetchMe()
  if (to.meta.public) return auth.user ? '/' : true
  if (!auth.user) return { path: '/login', query: to.fullPath !== '/' ? { next: to.fullPath } : {} }
  if (to.meta.staff && !auth.isStaff) return '/'
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · RT Kita` : 'RT Kita'
})

export default router
