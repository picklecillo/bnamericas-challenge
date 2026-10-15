import type { KeyDate } from './types'

/** Per-row errors keyed by index. The backend merges dates by label, so labels must be unique. */
export function keyDateErrors(dates: KeyDate[]): Record<number, string> {
  const errors: Record<number, string> = {}
  dates.forEach((kd, i) => {
    const label = kd.label.trim()
    if (!label) errors[i] = 'Label is required'
    else if (dates.findIndex((other) => other.label.trim() === label) !== i) errors[i] = 'Label already used'
    else if (!kd.date) errors[i] = 'Date is required'
  })
  return errors
}
