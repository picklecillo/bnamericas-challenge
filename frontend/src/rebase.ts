/**
 * After a 409, rebuild the user's edit on top of what the upstream holds now.
 *
 * Same per-field rule as backend/app/merge.py: a field only I changed keeps my value,
 * a field only they changed takes theirs, a conflicting field follows my pick.
 * The result becomes `yours` and `current` becomes the new `base`, so the resubmit
 * carries no stale changes that could undo someone else's work.
 */

import type { Editable, KeyDate } from './types'

export type Pick = 'theirs' | 'yours'

const SCALARS = ['name', 'sector', 'country', 'stage'] as const

export function rebase(base: Editable, yours: Editable, current: Editable, picks: Record<string, Pick>): Editable {
  const choose = <T,>(field: string, b: T, y: T, t: T): T => {
    if (y === b) return t
    if (picks[field] === 'theirs') return t
    return y
  }

  const result: Editable = { ...current, key_dates: [] }
  for (const name of SCALARS) {
    ;(result as unknown as Record<string, unknown>)[name] = choose(name, base[name], yours[name], current[name])
  }

  const b = byLabel(base.key_dates)
  const y = byLabel(yours.key_dates)
  const t = byLabel(current.key_dates)
  const labels = [...new Set([...current.key_dates, ...yours.key_dates].map((kd) => kd.label))]
  for (const label of labels) {
    const date = choose(`key_dates:${label}`, b.get(label), y.get(label), t.get(label))
    if (date !== undefined) result.key_dates.push({ label, date })
  }
  return result
}

function byLabel(dates: KeyDate[]): Map<string, string> {
  return new Map(dates.map((kd) => [kd.label, kd.date]))
}
