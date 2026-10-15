import { Autocomplete, Button, IconButton, Stack, TextField, Typography } from '@mui/material'
import type { KeyDate } from '../types'

// The labels the seed data uses (upstream/records_api/seed.py). Suggestions only; any label is allowed.
const KNOWN_LABELS = [
  'Feasibility study completed',
  'Tender launch',
  'Financial close',
  'Construction start',
  'Commercial operation',
]

interface Props {
  value: KeyDate[]
  onChange: (value: KeyDate[]) => void
  errors: Record<number, string>
}

export default function KeyDatesEditor({ value, onChange, errors }: Props) {
  const update = (i: number, patch: Partial<KeyDate>) =>
    onChange(value.map((kd, j) => (j === i ? { ...kd, ...patch } : kd)))
  const used = new Set(value.map((kd) => kd.label))

  return (
    <Stack spacing={1.5}>
      <Typography variant="subtitle1">Key dates</Typography>
      {value.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No key dates yet.
        </Typography>
      )}
      {value.map((kd, i) => (
        <Stack key={i} direction="row" spacing={1} alignItems="flex-start">
          <Autocomplete
            freeSolo
            options={KNOWN_LABELS.filter((l) => !used.has(l) || l === kd.label)}
            inputValue={kd.label}
            onInputChange={(_, label) => update(i, { label })}
            sx={{ flex: 1 }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Label"
                size="small"
                error={Boolean(errors[i])}
                helperText={errors[i]}
              />
            )}
          />
          <TextField
            label="Date"
            type="date"
            size="small"
            value={kd.date}
            onChange={(e) => update(i, { date: e.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <IconButton aria-label={`Remove ${kd.label || 'date'}`} onClick={() => onChange(value.filter((_, j) => j !== i))}>
            ×
          </IconButton>
        </Stack>
      ))}
      <div>
        <Button size="small" onClick={() => onChange([...value, { label: '', date: '' }])}>
          Add key date
        </Button>
      </div>
    </Stack>
  )
}
