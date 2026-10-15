import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { listProjects } from '../api'
import type { ProjectSummary } from '../types'
import { humanize } from '../format'

export default function ProjectList() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const load = useCallback(() => {
    setError(null)
    listProjects().then(setProjects, (e: Error) => setError(e.message))
  }, [])
  useEffect(load, [load])

  const q = query.trim().toLowerCase()
  const shown = projects?.filter((p) => !q || `${p.name} ${p.country} ${p.id}`.toLowerCase().includes(q))

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h5" component="h1">
          Projects
        </Typography>
        <TextField
          size="small"
          label="Search name, country or ID"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ width: 280 }}
        />
      </Stack>

      {error && (
        <Alert severity="error" action={<Button onClick={load}>Retry</Button>}>
          {error}
        </Alert>
      )}
      {!projects && !error && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress aria-label="Loading projects" />
        </Box>
      )}
      {shown && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Sector</TableCell>
                <TableCell>Country</TableCell>
                <TableCell>Stage</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {shown.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>
                    <RouterLink to={`/projects/${encodeURIComponent(p.id)}`}>{p.name}</RouterLink>
                  </TableCell>
                  <TableCell>{humanize(p.sector)}</TableCell>
                  <TableCell>{p.country}</TableCell>
                  <TableCell>{humanize(p.stage)}</TableCell>
                </TableRow>
              ))}
              {shown.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>No projects match “{query}”.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  )
}
