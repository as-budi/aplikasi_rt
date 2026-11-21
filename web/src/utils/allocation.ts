import type { Bill } from '@/api/types'

/** Pratinjau alokasi pembayaran, sama dengan aturan di backend (dues/services.py: allocate):
 *  uang + saldo titipan dipakai per BULAN UTUH, mulai dari bulan tertua; sisanya jadi titipan. */
export interface AllocItem {
  period: string
  amount: number
}

export interface AllocPreview {
  total: number // total tagihan yang dipilih
  paid: string[] // bulan yang akan lunas
  unpaid: string[] // bulan yang belum tertutup
  leftover: number // sisa uang (menjadi titipan, atau dikembalikan)
  shortfall: number // kekurangan untuk melunasi semua bulan terpilih
  refundable: number // bagian dari uang transfer ini yang bisa dikembalikan
}

export function previewAllocation(items: AllocItem[], received: number, credit: number): AllocPreview {
  const months = new Map<string, number>()
  for (const it of [...items].sort((a, b) => a.period.localeCompare(b.period))) {
    months.set(it.period, (months.get(it.period) ?? 0) + it.amount)
  }
  let available = Math.max(0, received) + credit
  const paid: string[] = []
  const unpaid: string[] = []
  let allocated = 0
  let unpaidTotal = 0
  for (const [period, amount] of months) {
    if (!unpaid.length && available >= amount) {
      paid.push(period)
      available -= amount
      allocated += amount
    } else {
      unpaid.push(period)
      unpaidTotal += amount
    }
  }
  return {
    total: allocated + unpaidTotal,
    paid,
    unpaid,
    leftover: available,
    shortfall: Math.max(0, unpaidTotal - available),
    refundable: unpaid.length ? 0 : Math.max(0, Math.min(available, received - allocated)),
  }
}

/** Item alokasi dari tagihan terpilih + bulan bayar di muka */
export function selectedItems(bills: Bill[], ids: number[], periods: string[], monthlyTotal: number): AllocItem[] {
  return [
    ...bills.filter((b) => ids.includes(b.id)).map((b) => ({ period: b.period, amount: b.amount })),
    ...periods.map((period) => ({ period, amount: monthlyTotal })),
  ]
}
