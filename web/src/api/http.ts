import axios from 'axios'

// Satu origin dengan Django: session cookie + CSRF, tanpa token di localStorage.
export const http = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

const FIELD_LABELS: Record<string, string> = {
  identifier: 'Username',
  password: 'Kata sandi',
  old_password: 'Kata sandi lama',
  new_password: 'Kata sandi baru',
  username: 'Username',
  nik: 'NIK',
  no_kk: 'No. KK',
  name: 'Nama',
  block: 'Blok',
  house_number: 'No. rumah',
  bills: 'Tagihan',
  file: 'File',
  amount: 'Nominal',
  event_at: 'Waktu kegiatan',
  review_note: 'Catatan',
  note: 'Catatan',
  title: 'Judul',
  body: 'Isi',
}

/** Ambil pesan kesalahan yang bisa dibaca warga dari respons Django REST Framework. */
export function errMsg(e: unknown, fallback = 'Terjadi kesalahan. Coba lagi.'): string {
  if (!axios.isAxiosError(e)) return fallback
  if (!e.response) return 'Tidak dapat terhubung ke server. Periksa koneksi internet.'
  if (e.response.status === 403 && !e.response.data) return 'Anda tidak punya akses.'
  const data: unknown = e.response.data
  if (Array.isArray(data) && data.length) return String(data[0])
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    if (typeof obj.detail === 'string') return obj.detail
    const first = Object.entries(obj)[0]
    if (first) {
      const [key, val] = first
      const msg = Array.isArray(val) ? String(val[0]) : typeof val === 'object' ? JSON.stringify(val) : String(val)
      return key === 'non_field_errors' ? msg : `${FIELD_LABELS[key] ?? key}: ${msg}`
    }
  }
  if (e.response.status >= 500) return 'Server sedang bermasalah. Coba beberapa saat lagi.'
  return fallback
}

/** Ambil semua halaman (dipakai untuk daftar kecil, mis. KK di satu RT). */
export async function fetchAll<T>(url: string, params: Record<string, unknown> = {}): Promise<T[]> {
  const { data } = await http.get<{ results: T[] }>(url, { params: { page_size: 500, ...params } })
  return data.results
}
