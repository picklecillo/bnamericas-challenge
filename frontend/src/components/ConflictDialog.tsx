import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Stack,
} from '@mui/material'
import { useState } from 'react'
import type { Pick } from '../rebase'
import type { Conflict } from '../types'

interface Props {
  conflicts: Conflict[]
  saving: boolean
  onResolve: (picks: Record<string, Pick>) => void
  onCancel: () => void
}

/** Neither side wins by default: every conflicting field needs an explicit pick. */
export default function ConflictDialog({ conflicts, saving, onResolve, onCancel }: Props) {
  const [picks, setPicks] = useState<Record<string, Pick>>({})
  const complete = conflicts.every((c) => picks[c.field])

  return (
    <Dialog open onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>Someone else changed the same fields</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Choose which value to keep for each field. Your other changes, and theirs, are kept as they are.
        </DialogContentText>
        <Stack spacing={2}>
          {conflicts.map((c) => (
            <FormControl key={c.field}>
              <FormLabel>{fieldLabel(c.field)}</FormLabel>
              <RadioGroup
                value={picks[c.field] ?? ''}
                onChange={(e) => setPicks({ ...picks, [c.field]: e.target.value as Pick })}
              >
                <FormControlLabel value="theirs" control={<Radio />} label={`Theirs: ${show(c.theirs)}`} />
                <FormControlLabel value="yours" control={<Radio />} label={`Mine: ${show(c.yours)}`} />
              </RadioGroup>
            </FormControl>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Back to editing</Button>
        <Button variant="contained" disabled={!complete || saving} onClick={() => onResolve(picks)}>
          Save with these choices
        </Button>
      </DialogActions>
    </Dialog>
  )
}

function fieldLabel(field: string): string {
  if (field.startsWith('key_dates:')) return `Key date "${field.slice('key_dates:'.length)}"`
  return field.charAt(0).toUpperCase() + field.slice(1)
}

function show(value: unknown): string {
  return value === null || value === undefined ? '(removed)' : String(value)
}
