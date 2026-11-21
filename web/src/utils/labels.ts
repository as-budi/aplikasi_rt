export const OCCUPANCY: Record<string, string> = { pemilik: 'Pemilik', kontrak: 'Kontrak', kos: 'Kos' }

export const RESIDENCE: Record<string, string> = { menetap: 'Menetap', singgah: 'Rumah singgah' }
export const RESIDENCE_HINT: Record<string, string> = {
  menetap: 'Dihuni sehari-hari',
  singgah: 'Hanya sesekali ditinggali',
}

export const CASH_CATEGORY: Record<string, string> = {
  saldo_awal: 'Saldo awal',
  donasi: 'Donasi / sumbangan',
  kebersihan: 'Kebersihan',
  keamanan: 'Keamanan',
  sosial: 'Sosial / santunan',
  kegiatan: 'Kegiatan warga',
  operasional: 'Operasional & ATK',
  perbaikan: 'Perbaikan fasilitas',
  lainnya: 'Lainnya',
}
export const INCOME_ONLY = ['saldo_awal', 'donasi']

export const RELATION: Record<string, string> = {
  kepala_keluarga: 'Kepala Keluarga',
  suami: 'Suami',
  istri: 'Istri',
  anak: 'Anak',
  orang_tua: 'Orang Tua',
  famili: 'Famili Lain',
  lainnya: 'Lainnya',
}

export const GENDER: Record<string, string> = { L: 'Laki-laki', P: 'Perempuan' }

export const RESIDENT_STATUS: Record<string, string> = { aktif: 'Aktif', pindah: 'Pindah', meninggal: 'Meninggal' }

export const METHOD: Record<string, string> = { tunai: 'Tunai', transfer: 'Transfer', qris: 'QRIS' }

export const ROLE: Record<string, string> = { admin: 'Admin', pengurus: 'Pengurus', warga: 'Warga' }

export const RELIGIONS = ['Islam', 'Kristen', 'Katolik', 'Hindu', 'Buddha', 'Konghucu', 'Lainnya']
export const MARITAL = ['Belum kawin', 'Kawin', 'Cerai hidup', 'Cerai mati']

export const CHANGE_FIELD: Record<string, string> = {
  name: 'Nama',
  nik: 'NIK',
  gender: 'Jenis kelamin',
  birth_place: 'Tempat lahir',
  birth_date: 'Tanggal lahir',
  phone: 'No. HP',
  occupation: 'Pekerjaan',
  religion: 'Agama',
  marital_status: 'Status perkawinan',
}
