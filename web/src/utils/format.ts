const TZ = 'Asia/Jakarta'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
const MONTHS_LONG = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

export const rp = (n: number | null | undefined) => 'Rp' + (n ?? 0).toLocaleString('id-ID')

export function periodLabel(period: string, long = false): string {
  const [y, m] = period.split('-').map(Number)
  return `${(long ? MONTHS_LONG : MONTHS)[m - 1]} ${y}`
}

export const monthShort = (period: string) => MONTHS[Number(period.slice(5, 7)) - 1]

function toDate(iso: string): Date {
  // 'YYYY-MM-DD' dianggap tanggal WIB, bukan UTC
  return iso.length === 10 ? new Date(`${iso}T00:00:00+07:00`) : new Date(iso)
}

export function dateLabel(iso: string | null | undefined): string {
  if (!iso) return '—'
  return toDate(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric', timeZone: TZ })
}

export function dateTimeLabel(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = toDate(iso)
  const day = d.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: TZ })
  const time = d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', timeZone: TZ })
  return `${day} · ${time} WIB`
}

/** Tanggal hari ini di WIB, format YYYY-MM-DD */
export const todayISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date())
export const currentYear = () => Number(todayISO().slice(0, 4))
export const currentPeriod = () => todayISO().slice(0, 7)

/** Nilai untuk <input type="datetime-local"> dari ISO server (sudah dalam WIB) */
export function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(d)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
}

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase()
