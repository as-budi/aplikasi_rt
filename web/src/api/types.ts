export type Role = 'admin' | 'pengurus' | 'warga'
export type BillStatus = 'belum_bayar' | 'menunggu_verifikasi' | 'lunas'
export type ReviewStatus = 'pending' | 'diterima' | 'ditolak' | 'disetujui'
export type PayMethod = 'tunai' | 'transfer' | 'qris'
export type PostType = 'berita' | 'kegiatan'
export type ResidenceStatus = 'menetap' | 'singgah'
export type CashKind = 'pemasukan' | 'pengeluaran'

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Me {
  id: number
  username: string
  name: string
  role: Role
  phone: string
  email: string
  is_staff_rt: boolean
  resident: number | null
  household_id: number | null
  household_label: string | null
}

export interface Resident {
  id: number
  household?: number
  nik?: string
  nik_masked?: string
  name: string
  gender: 'L' | 'P'
  birth_place: string
  birth_date: string | null
  religion: string
  marital_status: string
  relation: string
  occupation: string
  phone: string
  status: 'aktif' | 'pindah' | 'meninggal'
  age: number | null
  has_account?: boolean
  username?: string | null
}

export interface HouseholdListItem {
  id: number
  label: string
  block: string
  house_number: string
  address: string
  occupancy: string
  residence_status: ResidenceStatus
  is_active: boolean
  head_name: string
  head_phone: string
  member_count: number
  no_kk_masked: string
  current_status: BillStatus | null
  credit: number
}

export interface HouseholdDetail extends HouseholdListItem {
  no_kk: string
  since: string | null
  members: Resident[]
  created_at: string
}

export interface HouseholdOwn {
  id: number
  label: string
  block: string
  house_number: string
  address: string
  occupancy: string
  residence_status: ResidenceStatus
  since: string | null
  no_kk_masked: string
  credit: number
  members: Resident[]
}

export interface HouseholdWrite {
  id?: number
  no_kk: string
  block: string
  house_number: string
  address: string
  occupancy: string
  residence_status: ResidenceStatus
  since: string | null
  is_active?: boolean
}

export interface ChangeRequest {
  id: number
  household: number
  household_label: string
  resident: number | null
  resident_name: string | null
  requested_by_name: string | null
  changes: Record<string, { old: string | null; new: string | null }>
  note: string
  status: 'pending' | 'disetujui' | 'ditolak'
  review_note: string
  reviewed_by_name: string | null
  reviewed_at: string | null
  created_at: string
}

export interface FeeType {
  id: number
  name: string
  amount: number
  period: 'bulanan' | 'sekali'
  description: string
}

export interface Bill {
  id: number
  household: number
  household_label: string
  fee_type: number
  fee_type_name: string
  period: string
  amount: number
  status: BillStatus
  payment: number | null
  paid_at: string | null
  method: PayMethod | null
}

export interface BillMini {
  id: number
  period: string
  fee_type_name: string
  amount: number
  status: BillStatus
}

export interface PaymentProof {
  id: number
  household: number
  household_label: string
  head_name: string
  household_credit: number
  uploaded_by_name: string | null
  bills: BillMini[]
  amount: number
  transfer_date: string
  method: PayMethod
  note: string
  status: 'pending' | 'diterima' | 'ditolak'
  review_note: string
  verified_by_name: string | null
  verified_at: string | null
  created_at: string
  file_url: string
  file_type: 'image' | 'pdf'
}

export interface Summary {
  year: number
  periods: string[]
  rows: {
    household_id: number
    label: string
    head_name: string
    cells: Record<string, BillStatus | null>
    arrears?: number
    credit?: number
  }[]
  income?: Record<string, number>
}

export interface Post {
  id: number
  type: PostType
  title: string
  body: string
  event_at: string | null
  location: string
  is_pinned: boolean
  is_published: boolean
  published_at: string | null
  author_name: string | null
  created_at: string
  updated_at: string
}

export interface Dashboard {
  period: string
  me: {
    household_id: number
    household_label: string
    head_name: string
    current_status: BillStatus | null
    current_bills: Bill[]
    arrears_total: number
    arrears_months: number
    credit: number
  } | null
  staff: {
    households: number
    residents: number
    billed_households: number
    paid_households: number
    income: number
    target: number
    pending_proofs: number
    pending_changes: number
    pending_registrations: number
    top_arrears: { household_id: number; label: string; head_name: string; months: number; total: number }[]
  } | null
  cash_balance: number
  upcoming_events: Post[]
  latest_news: Post[]
}

export interface CashEntry {
  id: number
  kind: CashKind
  kind_label: string
  category: string
  category_label: string
  description: string
  amount: number
  date: string
  receipt_url: string | null
  recorded_by_name: string | null
  created_at: string
}

export interface CashReport {
  year: number
  opening_balance: number
  closing_balance: number
  totals: { iuran: number; other_income: number; expense: number }
  months: { period: string; iuran: number; other_income: number; expense: number; balance: number }[]
  expense_by_category: { category: string; label: string; amount: number }[]
}

export interface RegisterMember {
  name: string
  nik: string
  gender: 'L' | 'P'
  birth_place: string
  birth_date: string | null
  religion: string
  marital_status: string
  relation: string
  occupation: string
  phone: string
}

export interface Registration {
  id: number
  name: string
  house_label: string
  username: string
  phone: string
  status: 'pending' | 'disetujui' | 'ditolak'
  review_note: string
  reviewed_by_name: string | null
  reviewed_at: string | null
  household: number | null
  household_label: string | null
  data: {
    household?: { no_kk: string; block: string; house_number: string; address: string; occupancy: string; residence_status: ResidenceStatus; since: string | null }
    members?: RegisterMember[]
  }
  matching_household: { id: number; label: string; head_name: string } | null
  created_at: string
}

/** Baris buku kas gabungan: transaksi kas atau pemasukan iuran */
export interface LedgerRow {
  source: 'kas' | 'iuran'
  id: number
  kind: CashKind
  category: string
  category_label: string
  description: string
  amount: number
  date: string
  receipt_url: string | null
  recorded_by_name: string | null
  household_id: number | null
}

/** Bulan mendatang yang bisa dibayar di muka oleh satu KK */
export interface PrepayOptions {
  periods: string[]
  fees: { name: string; amount: number }[]
  monthly_total: number
  credit: number
}
