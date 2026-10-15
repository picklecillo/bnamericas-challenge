# Session 02: Backend

Tool: Claude Code (Opus 5.5). Date: 2026-10-15.

Goal: build the FastAPI backend that sits between the browser and the upstream, including safe concurrent editing.

---

## Prompt 1

> let's start working on the backend. read the root's readme for more context. ask any clarifying questions

### What Claude did

- Read the root `README.md`, `upstream/README.md`, `upstream/records_api/main.py`, the seed data and the session-01 log.
- Proposed a design before asking anything: the backend is stateless (3 instances, plus a nightly import that writes upstream directly), so upstream's current state is the only truth. Saves use a per-field three-way merge of `base` (what the form loaded), `theirs` (upstream now) and `yours` (the form now).
- Asked four questions. Answers:

| Question | Answer |
|---|---|
| What counts as "the same field" for `key_dates`? | Each label is one field |
| How to close the race window between our GET and PUT across 3 instances | Accept it and document it (no Redis lock) |
| Should `linked_companies` be editable? | No, pass-through only |
| Workflow | TDD, merge logic first |

- Wrote a plan (plan mode), which the user approved. Then built it test-first using the `tdd` skill: one failing test, then the minimal code to pass it.

### Build log

| Step | Test (behavior) | Result |
|---|---|---|
| 1 | User changes name, nobody else did → taken | RED → GREEN |
| 2 | Different fields changed by each side → both kept | Passed at once |
| 3 | Same field, different values → conflict with base/theirs/yours | RED → GREEN |
| 4 | Same field, same value → no conflict | Passed at once |
| 5 | Key dates: different labels changed → both kept | RED → GREEN (generalized to a per-key rule) |
| 6–7 | Same label moved by both → conflict; add label; remove vs concurrent move → conflict; plain remove | Passed at once (step 5 covered them) |
| 8 | Duplicate key date labels → rejected | RED → GREEN |
| 9 | `GET /api/projects` returns slim summaries | RED → GREEN |
| 10 | `GET /api/projects/{id}` detail; unknown → 404 | RED → GREEN |
| 11 | Two stale saves on different fields → both stored | RED → GREEN |
| 12 | Same-field stale save → 409, nothing written; resubmit on `current` → 200 | RED → GREEN |
| 13 | PUT 504 that landed → 200, one PUT; 504 that was lost → retried | RED → GREEN |
| 14 | Lost 504 plus a concurrent write meanwhile → both kept; repeated 504 → 502; upstream down → 502; linked companies changed elsewhere are preserved | Passed at once |

Steps that "passed at once" were kept as spec. To check the step-14 tests weren't passing vacuously, Claude broke the retry on purpose (reused stale state instead of re-reading). The concurrent-write test failed as it should, and the code was restored.

### Friction

- The session-01 Bash hook blocked several harmless commands because they contained the word "upstream", e.g. a heredoc writing `backend/pyproject.toml` whose description says "upstream", and `sed` on `backend/app/service.py`. Claude switched to the Write/Edit tools for those files. This is the known false-positive limit noted in session 01.
- Starlette prints a deprecation warning saying it wants `httpx2` for `TestClient`. Left as is.

### Verification

- `cd backend && uv run pytest`: 22 passed.
- Smoke test against the real upstream (default 10% slow GETs and 10% 504s), through the backend:
  - list returns 30 projects
  - two stale saves on different fields: both 200, both changes kept
  - same field: 409 with the conflict
  - key dates on different labels: both kept
  - 60 saves in a row: all 200, 0 mismatches on re-read. The upstream log shows 5 of 67 PUTs answered 504, so the retry path ran.

### Not done yet

Frontend, `DECISIONS.md`, README rewrite.
