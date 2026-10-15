# Project editor

An internal editor for infrastructure project records. A React + MUI frontend talks to a FastAPI backend, which sits in front of the **upstream records API** (owned by another team, in `upstream/`, untouched). The browser never calls the upstream directly.

Two people can edit the same project at once. Changes to different fields both survive. Changes to the same field are never silently overwritten: the person saving second sees both values and picks one. Design and trade-offs are in [`DECISIONS.md`](DECISIONS.md).

## Start it

### With Docker (recommended)

Requires Docker with Compose v2.

```sh
make up      # build if needed and start everything in the background
make logs    # follow all logs; `make logs s=backend` for one service
make down    # stop
make build   # rebuild images (after changing dependencies) and start
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 (OpenAPI docs at `/docs`) |
| Upstream | http://localhost:8081 (OpenAPI docs at `/docs`) |
| Redis | localhost:6379 (save locks) |

Host ports can be changed with `FRONTEND_PORT`, `BACKEND_PORT` and `UPSTREAM_PORT`. The upstream's awkward habits stay on by default. Turn them off with `UPSTREAM_SLOW_RATE=0 UPSTREAM_TIMEOUT_RATE=0 make up`.

Frontend and backend source is bind-mounted, so edits reload live. The upstream image is built from `upstream/` as-is. Its Dockerfile lives in `docker/` because nothing inside `upstream/` may change.

### Without Docker

Requires [uv](https://docs.astral.sh/uv/), Node 24 and a Redis on `127.0.0.1:6379` (for example `docker compose up -d redis`). Use three terminals:

```sh
cd upstream && uv run upstream                         # :8081
cd backend  && uv run uvicorn app.main:app --reload     # :8000
cd frontend && npm install && npm run dev               # :5173, proxies /api to :8000
```

The backend reads `UPSTREAM_URL` (default `http://127.0.0.1:8081`), `UPSTREAM_API_KEY` (default `local-dev-key`) and `REDIS_URL` (default `redis://127.0.0.1:6379/0`). The frontend dev server reads `BACKEND_URL` (default `http://127.0.0.1:8000`).

## Tests

```sh
# in Docker
docker compose run --rm --no-deps backend uv run pytest
docker compose exec frontend npm test

# or locally
cd backend && uv run pytest
cd frontend && npm test
```

- **Backend (32 tests):** the three-way merge rules and the API against a fake upstream: list, detail, 404, concurrent saves on different fields and on the same field, 504s that did and did not land, and the upstream being down. Plus the save lock against an in-memory Redis (fakeredis): waiting, renewal, token-checked release, `503` when busy or when Redis is down, and two overlapping saves that both survive.
- **Frontend (8 tests):** the client-side rebase after a conflict, plus the edit page flow: save, conflict dialog with no default pick, resubmit, and error display.

## Race detector

`loadtest/` holds a [Locust](https://locust.io) run that measures the lost-update gap described in `DECISIONS.md`. With the stack running:

```sh
make race                          # 20 editors, 30 s, against http://localhost:8000
make race args="-u 50 -t 60s"      # any Locust flags
HOT_PROJECTS=1 make race           # how many projects the editors pile onto (default 2)
```

Each simulated editor loads a hot project and adds a key date with a unique label. Adds of distinct labels never conflict, so every save answered with `200` must still be on the record at the end. The report counts the ones that are missing; saves that ended in `502` are listed apart, since nobody knows whether they landed, and so are `503`s (the save waited too long for the lock and wrote nothing). To spread requests over several backend instances, set `BACKEND_HOSTS=http://host1:8000,http://host2:8000`. The run exits `1` if any confirmed save was lost.

## Layout

```
backend/    FastAPI app
  app/upstream.py   thin upstream client; 404/504/timeouts become exceptions
  app/merge.py      per-field three-way merge (each key date label is one field)
  app/service.py    save: lock, read current, merge, PUT, verify ambiguous 504s
  app/locks.py      per-project save lock in Redis, shared by all instances
  app/models.py     the narrow shapes the browser sees
frontend/   Vite + React + TypeScript + MUI
  src/api.ts        the only module that does HTTP (all under /api)
  src/rebase.ts     rebuilds an edit on top of the current record after a 409
  src/pages/        project list, project edit form
loadtest/   Locust race detector for the save path
docker/     upstream image (kept outside upstream/)
upstream/   the records API, owned by another team. Read-only for us
ai-trail/   session-by-session log of how the AI tooling was set up and used
```

## What works

- The project list, with search by name, country or ID.
- The edit form for name, sector, country, stage and key dates (add, remove, rename, re-date). Linked companies are shown read-only.
- Safe concurrent saves through a three-way merge against the upstream's current state. Same-field conflicts return `409`, and the UI asks for an explicit pick per field.
- One save at a time per project, across every backend instance, through a lock in Redis. If Redis is down, saves answer `503` instead of running unguarded.
- Ambiguous upstream `504`s are verified by re-reading, never blindly retried. If saves keep failing, the backend returns `502`, and the form keeps your edit.

## What does not, or is not built

- **A narrower race window remains.** Saves through our backend now take a per-project lock in Redis, so they no longer overwrite each other: the race detector went from 13% of confirmed saves lost to 0. The nightly import skips our backend, so a write from it that lands between our read and our write can still be overwritten. Under heavy contention some saves wait up to 10 s and get a `503` ("try again"). The race detector has not yet been run against several instances. See `DECISIONS.md`.
- **Bad import data.** A record with duplicate key date labels, which the nightly import could write, fails validation, and its edit page shows an error.
- **Not built:** editing linked companies, user identity ("someone else changed…" never says who), pagination and caching of the list, live updates of an open record, a warning when leaving with unsaved changes, and a production build or deploy. The Docker setup is for development only.

## AI tooling

Built with Claude Code. The session logs are in [`ai-trail/`](ai-trail/). The setup:

- `CLAUDE.md` states the hard rule: never change `upstream/`.
- `.claude/hooks/` blocks edits and shell commands that would modify `upstream/`. The shell hook matches text, so it sometimes blocks harmless commands that only mention "upstream" (logged in the sessions).

---

All projects, companies and places in this repository are fictional.
