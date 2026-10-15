// Mirrors backend/app/models.py.

export const SECTORS = ['energy', 'mining', 'water', 'transport', 'oil_and_gas', 'ict'] as const
export const STAGES = ['idea', 'feasibility', 'tender', 'financing', 'construction', 'operation', 'cancelled'] as const

export type Sector = (typeof SECTORS)[number]
export type Stage = (typeof STAGES)[number]

export interface KeyDate {
  label: string
  date: string // YYYY-MM-DD
}

export interface Editable {
  name: string
  sector: Sector
  country: string
  stage: Stage
  key_dates: KeyDate[]
}

export interface LinkedCompany {
  name: string
  role: string
}

export interface ProjectDetail extends Editable {
  id: string
  linked_companies: LinkedCompany[]
}

export interface ProjectSummary {
  id: string
  name: string
  sector: Sector
  country: string
  stage: Stage
}

/** One field both sides changed. `field` is a scalar name or `key_dates:<label>`; a date value of null means "no such date". */
export interface Conflict {
  field: string
  base: unknown
  theirs: unknown
  yours: unknown
}

export function editableOf(p: Editable): Editable {
  return {
    name: p.name,
    sector: p.sector,
    country: p.country,
    stage: p.stage,
    key_dates: p.key_dates.map((kd) => ({ ...kd })),
  }
}
