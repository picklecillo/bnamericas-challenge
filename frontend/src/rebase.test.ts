import { describe, expect, it } from 'vitest'
import { rebase } from './rebase'
import type { Editable } from './types'

const base: Editable = {
  name: 'Solar Park',
  sector: 'energy',
  country: 'Chile',
  stage: 'idea',
  key_dates: [
    { label: 'Tender launch', date: '2027-01-01' },
    { label: 'Financial close', date: '2027-06-01' },
  ],
}

describe('rebase', () => {
  it('keeps my change and takes their change on different fields', () => {
    const yours = { ...base, name: 'Solar Park II' }
    const current = { ...base, stage: 'tender' as const }

    expect(rebase(base, yours, current, {})).toEqual({ ...base, name: 'Solar Park II', stage: 'tender' })
  })

  it('resolves a scalar conflict by my pick', () => {
    const yours = { ...base, name: 'Mine' }
    const current = { ...base, name: 'Theirs' }

    expect(rebase(base, yours, current, { name: 'yours' }).name).toBe('Mine')
    expect(rebase(base, yours, current, { name: 'theirs' }).name).toBe('Theirs')
  })

  it('treats each key date label as its own field', () => {
    const yours = {
      ...base,
      key_dates: [
        { label: 'Tender launch', date: '2027-02-02' },
        { label: 'Financial close', date: '2027-06-01' },
      ],
    }
    const current = {
      ...base,
      key_dates: [
        { label: 'Tender launch', date: '2027-01-01' },
        { label: 'Financial close', date: '2027-09-09' },
      ],
    }

    expect(rebase(base, yours, current, {}).key_dates).toEqual([
      { label: 'Tender launch', date: '2027-02-02' },
      { label: 'Financial close', date: '2027-09-09' },
    ])
  })

  it('keeps dates added on either side and drops dates removed on one side', () => {
    const yours = { ...base, key_dates: [...base.key_dates, { label: 'Construction start', date: '2028-01-01' }] }
    const current = { ...base, key_dates: [base.key_dates[0]] }

    expect(rebase(base, yours, current, {}).key_dates).toEqual([
      { label: 'Tender launch', date: '2027-01-01' },
      { label: 'Construction start', date: '2028-01-01' },
    ])
  })

  it('resolves a key date conflict by my pick, including a removal', () => {
    const yours = { ...base, key_dates: [base.key_dates[0]] } // I removed Financial close
    const current = {
      ...base,
      key_dates: [base.key_dates[0], { label: 'Financial close', date: '2027-12-12' }], // they moved it
    }

    expect(rebase(base, yours, current, { 'key_dates:Financial close': 'yours' }).key_dates).toEqual([
      { label: 'Tender launch', date: '2027-01-01' },
    ])
    expect(rebase(base, yours, current, { 'key_dates:Financial close': 'theirs' }).key_dates).toEqual(
      current.key_dates,
    )
  })
})
