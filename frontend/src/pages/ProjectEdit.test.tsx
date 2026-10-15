import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ProjectDetail } from '../types'
import ProjectEdit from './ProjectEdit'

const loaded: ProjectDetail = {
  id: 'p1',
  name: 'Solar Park',
  sector: 'energy',
  country: 'Chile',
  stage: 'idea',
  key_dates: [{ label: 'Tender launch', date: '2027-01-01' }],
  linked_companies: [{ name: 'Varelo Energia SA', role: 'owner' }],
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${id}`]}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectEdit />} />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => vi.restoreAllMocks())

describe('ProjectEdit', () => {
  it('saves my edit with the loaded record as base', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    fetch.mockResolvedValueOnce(json(200, loaded))
    fetch.mockResolvedValueOnce(json(200, { ...loaded, name: 'Solar Park II' }))
    renderAt('p1')

    const name = await screen.findByLabelText('Name')
    await userEvent.clear(name)
    await userEvent.type(name, 'Solar Park II')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await screen.findByText('Saved')
    const [url, init] = fetch.mock.calls[1]
    expect(url).toBe('/api/projects/p1')
    expect(init?.method).toBe('PUT')
    const body = JSON.parse(init?.body as string)
    expect(body.base.name).toBe('Solar Park')
    expect(body.yours.name).toBe('Solar Park II')
  })

  it('on conflict, makes me pick, then resubmits on top of the current record', async () => {
    const current = { ...loaded, name: 'Solar Park (theirs)', stage: 'tender' }
    const fetch = vi.spyOn(globalThis, 'fetch')
    fetch.mockResolvedValueOnce(json(200, loaded))
    fetch.mockResolvedValueOnce(
      json(409, {
        detail: 'conflict',
        conflicts: [{ field: 'name', base: 'Solar Park', theirs: 'Solar Park (theirs)', yours: 'Solar Park (mine)' }],
        current,
      }),
    )
    fetch.mockResolvedValueOnce(json(200, { ...current, name: 'Solar Park (mine)' }))
    renderAt('p1')

    const name = await screen.findByLabelText('Name')
    await userEvent.clear(name)
    await userEvent.type(name, 'Solar Park (mine)')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    const dialog = await screen.findByRole('dialog')
    const resolve = screen.getByRole('button', { name: 'Save with these choices' })
    expect(resolve).toBeDisabled() // nobody wins by default
    await userEvent.click(screen.getByRole('radio', { name: /Mine: Solar Park \(mine\)/ }))
    await userEvent.click(resolve)

    await screen.findByText('Saved')
    expect(dialog).not.toBeInTheDocument()
    const body = JSON.parse(fetch.mock.calls[2][1]?.body as string)
    expect(body.base.name).toBe('Solar Park (theirs)')
    expect(body.base.stage).toBe('tender')
    expect(body.yours.name).toBe('Solar Park (mine)')
    expect(body.yours.stage).toBe('tender') // their non-conflicting change survives
  })

  it('shows an error and keeps my edit when the backend fails', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    fetch.mockResolvedValueOnce(json(200, loaded))
    fetch.mockResolvedValueOnce(json(502, { detail: 'The records service is unavailable. Try again.' }))
    renderAt('p1')

    const name = await screen.findByLabelText('Name')
    await userEvent.type(name, '!')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await screen.findByText('The records service is unavailable. Try again.')
    await waitFor(() => expect(screen.getByLabelText('Name')).toHaveValue('Solar Park!'))
  })
})
