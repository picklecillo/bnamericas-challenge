import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { ApiError, SaveConflict, getProject, saveProject } from '../api'
import ConflictDialog from '../components/ConflictDialog'
import { humanize } from '../format'
import KeyDatesEditor from '../components/KeyDatesEditor'
import { keyDateErrors } from '../validation'
import { rebase, type Pick } from '../rebase'
import { SECTORS, STAGES, editableOf, type Editable, type ProjectDetail } from '../types'

/**
 * `base` is the record as the form last loaded it; `form` is what the user has now.
 * Both go to the backend on save so it can merge against whatever changed meanwhile.
 */
export default function ProjectEdit() {
  const { id = '' } = useParams()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [base, setBase] = useState<Editable | null>(null)
  const [form, setForm] = useState<Editable | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [conflict, setConflict] = useState<SaveConflict | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false
    setProject(null)
    setLoadError(null)
    getProject(id).then(
      (p) => !cancelled && load(p),
      (e: ApiError) => !cancelled && setLoadError(e.message),
    )
    return () => {
      cancelled = true
    }
  }, [id])

  function load(p: ProjectDetail) {
    setProject(p)
    setBase(editableOf(p))
    setForm(editableOf(p))
  }

  async function save(base: Editable, yours: Editable) {
    setSaving(true)
    setSaveError(null)
    try {
      load(await saveProject(id, base, normalize(yours)))
      setConflict(null)
      setSaved(true)
    } catch (e) {
      if (e instanceof SaveConflict) setConflict(e)
      else setSaveError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  function resolve(picks: Record<string, Pick>) {
    if (!conflict || !base || !form) return
    const current = editableOf(conflict.current)
    const rebased = rebase(base, normalize(form), current, picks)
    setProject(conflict.current)
    setBase(current)
    setForm(rebased)
    void save(current, rebased)
  }

  if (loadError) {
    return (
      <Alert severity="error" action={<Button component={RouterLink} to="/projects">Back</Button>}>
        {loadError}
      </Alert>
    )
  }
  if (!project || !base || !form) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress aria-label="Loading project" />
      </Box>
    )
  }

  const dateErrors = keyDateErrors(form.key_dates)
  const valid = form.name.trim() !== '' && form.country.trim() !== '' && Object.keys(dateErrors).length === 0
  const dirty = JSON.stringify(normalize(form)) !== JSON.stringify(base)
  const set = <K extends keyof Editable>(key: K, value: Editable[K]) => setForm({ ...form, [key]: value })

  return (
    <Stack spacing={3}>
      <Box>
        <Button component={RouterLink} to="/projects" size="small">
          ← All projects
        </Button>
        <Typography variant="h5" component="h1" sx={{ mt: 1 }}>
          {project.name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {project.id}
        </Typography>
      </Box>

      <Paper
        component="form"
        variant="outlined"
        sx={{ p: 3 }}
        onSubmit={(e) => {
          e.preventDefault()
          void save(base, form)
        }}
      >
        <Stack spacing={2.5}>
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            error={form.name.trim() === ''}
            helperText={form.name.trim() === '' ? 'Name is required' : undefined}
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              select
              label="Sector"
              value={form.sector}
              onChange={(e) => set('sector', e.target.value as Editable['sector'])}
              sx={{ flex: 1 }}
            >
              {SECTORS.map((s) => (
                <MenuItem key={s} value={s}>
                  {humanize(s)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Stage"
              value={form.stage}
              onChange={(e) => set('stage', e.target.value as Editable['stage'])}
              sx={{ flex: 1 }}
            >
              {STAGES.map((s) => (
                <MenuItem key={s} value={s}>
                  {humanize(s)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Country"
              value={form.country}
              onChange={(e) => set('country', e.target.value)}
              error={form.country.trim() === ''}
              helperText={form.country.trim() === '' ? 'Country is required' : undefined}
              sx={{ flex: 1 }}
            />
          </Stack>

          <Divider />
          <KeyDatesEditor value={form.key_dates} onChange={(v) => set('key_dates', v)} errors={dateErrors} />

          <Divider />
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Linked companies
            </Typography>
            <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
              {project.linked_companies.map((c) => (
                <Chip key={`${c.name}-${c.role}`} label={`${c.name} · ${humanize(c.role)}`} variant="outlined" />
              ))}
              {project.linked_companies.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  None
                </Typography>
              )}
            </Stack>
          </Box>

          {saveError && <Alert severity="error">{saveError}</Alert>}

          <Stack direction="row" spacing={1} sx={{ justifyContent: 'flex-end' }}>
            <Button disabled={!dirty || saving} onClick={() => setForm(editableOf(base))}>
              Discard changes
            </Button>
            <Button type="submit" variant="contained" disabled={!dirty || !valid || saving}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {conflict && (
        <ConflictDialog
          conflicts={conflict.conflicts}
          saving={saving}
          onResolve={resolve}
          onCancel={() => setConflict(null)}
        />
      )}
      <Snackbar open={saved} autoHideDuration={3000} onClose={() => setSaved(false)} message="Saved" />
    </Stack>
  )
}

function normalize(e: Editable): Editable {
  return {
    ...e,
    name: e.name.trim(),
    country: e.country.trim(),
    key_dates: e.key_dates.map((kd) => ({ label: kd.label.trim(), date: kd.date })),
  }
}
