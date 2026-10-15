// The only module that does HTTP. Everything goes to our backend under /api.

import type { Conflict, Editable, ProjectDetail, ProjectSummary } from './types'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Someone else changed some of the same fields. `current` is the record as it stands now. */
export class SaveConflict extends Error {
  readonly conflicts: Conflict[]
  readonly current: ProjectDetail
  constructor(conflicts: Conflict[], current: ProjectDetail) {
    super('Save conflict')
    this.conflicts = conflicts
    this.current = current
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  }
  const body = await response.json().catch(() => null)
  if (response.ok) return body as T
  if (response.status === 409 && body?.conflicts) throw new SaveConflict(body.conflicts, body.current)
  throw new ApiError(response.status, messageOf(body) ?? `Request failed (${response.status})`)
}

function messageOf(body: unknown): string | undefined {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join('; ') // FastAPI 422
  return undefined
}

export const listProjects = () => request<ProjectSummary[]>('/api/projects')

export const getProject = (id: string) => request<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`)

/** `base` is what the form loaded, `yours` what it holds now. Throws SaveConflict on 409. */
export const saveProject = (id: string, base: Editable, yours: Editable) =>
  request<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base, yours }),
  })
