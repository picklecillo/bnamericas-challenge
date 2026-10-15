import { AppBar, Container, CssBaseline, Toolbar, Typography } from '@mui/material'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProjectEdit from './pages/ProjectEdit'
import ProjectList from './pages/ProjectList'

export default function App() {
  return (
    <BrowserRouter>
      <CssBaseline />
      <AppBar position="static" elevation={0}>
        <Toolbar variant="dense">
          <Typography variant="h6" component="div">
            Project editor
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/:id" element={<ProjectEdit />} />
        </Routes>
      </Container>
    </BrowserRouter>
  )
}
