# Session 03: Frontend

Tool: Claude Code (Opus 5.5). Date: 2026-10-15.

Goal: build the React + MUI frontend with a project list, an edit form for the core fields and key dates, and a UI for resolving save conflicts.

---

## Prompt 1

> let's start working on the frontend. check the README for context. ask any clarifying questions

### What Claude did

- Read the root `README.md`, `upstream/README.md`, the backend (`main.py`, `models.py`, `service.py`, `merge.py`) and the session-02 log, so the UI matches the backend contract: `PUT {base, yours}`, which answers 200, or 409 with `{conflicts, current}`.
- Asked four questions. Answers:

| Question | Answer |
|---|---|
| How does the user resolve a 409? | For each conflicting field, pick theirs or mine. No default. Non-conflicting fields merge automatically |
| Key date labels | MUI Autocomplete with `freeSolo`: suggests the 5 seed labels, allows any label |
| Layout | Two routes: `/projects` (list) and `/projects/:id` (edit) |
| Testing | TDD only for the key logic: the rebase function and the save/conflict flow |

### Design

- Stack: Vite + React 19 + TypeScript + MUI 7 + react-router 7, in `frontend/`. In dev, Vite proxies `/api` to the backend (`BACKEND_URL`, default `127.0.0.1:8000`), so the browser never talks to the upstream.
- `api.ts` is the only module that makes HTTP calls. A 409 becomes a typed `SaveConflict` error. Other failures become `ApiError` with the backend's `detail`.
- **Rebase after a conflict** (`rebase.ts`): when a 409 comes back, the form is rebuilt on top of `current`. Fields only I changed keep my value. Fields only they changed take theirs. Conflicting fields follow my pick. The resubmit then sends `base = current`. Resubmitting the old form with the new base would treat every field someone else changed as my edit, and would silently revert their work. This is the same per-field and per-label rule as `backend/app/merge.py`.
- The conflict dialog's "Save with these choices" button stays disabled until every field has a pick, so neither side wins silently.
- Client-side validation mirrors the backend: name and country required, key date labels non-empty and unique (the merge keys dates by label), and a date on every row. Labels and text are trimmed before sending.
- Linked companies are shown read-only as chips, matching the backend's pass-through.

### Build log

| Step | Test (behavior) | Result |
|---|---|---|
| 1 | `rebase`: my change and their change on different fields both kept | RED (module missing) → GREEN |
| 2 | `rebase`: scalar conflict follows my pick | GREEN with step 1 |
| 3 | `rebase`: each key date label is its own field | GREEN |
| 4 | `rebase`: dates added on either side kept, removed on one side dropped | GREEN |
| 5 | `rebase`: remove vs. concurrent move is resolved by my pick | GREEN |
| 6 | Edit page: save sends the loaded record as `base` | RED (page missing) → GREEN |
| 7 | Edit page: 409 → dialog, button disabled until I pick → resubmit carries `base=current`, my pick, and their non-conflicting `stage` change | GREEN |
| 8 | Edit page: 502 shows the backend message and keeps my edit | GREEN |

### Friction

- The session-01 Bash hook blocked a heredoc writing `frontend/src/rebase.ts`, because a code comment contains the word "upstream". Claude switched to the Write tool. This is the same known false positive as in session 02.
- RTL's auto-cleanup didn't run because vitest globals are off. Tests leaked DOM into each other ("Found multiple elements"). Fixed with an explicit `afterEach(cleanup)` in `test-setup.ts`.
- `vite.config.ts` read `process.env` without `@types/node`, which broke `tsc -b`. Added the dev dependency.
- ESLint `react-refresh/only-export-components`: moved `keyDateErrors` out of the component file into `validation.ts`.

### Verification

- `npm test`: 8 passed. `npm run build` and `npm run lint` are clean.
- Smoke test against the real upstream through the Vite proxy (`localhost:5173/api`): list returns 30, first save 200, stale same-field save 409 on `name`, and the SPA deep link `/projects/x` serves the page.
- The UI was not checked in a browser in this session. That is left to the user.

### Cut

- No unsaved-changes guard when navigating away from the edit page.
- No automatic refresh when someone else edits a record that is open. The conflict shows up on save instead.
- No editing of linked companies (out of scope, per session 02).
