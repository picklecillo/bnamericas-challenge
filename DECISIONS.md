# Decisions

## What I chose

**A stateless backend, with the upstream as the only source of truth.** Production runs three backend instances, and a nightly import writes to the upstream directly. Any version table, cache or lock held inside our backend would be wrong the moment the import runs or another instance saves. So every save reads the upstream's current record and works from that. Any instance can serve any request. The one piece of shared state is a short-lived save lock in Redis (below). It decides who writes when; it holds no data.

**A three-way merge per field on save** (`backend/app/merge.py`). The browser sends `base` (the record as the form loaded it) and `yours` (the form now). The backend reads `theirs` (the upstream now) and applies one rule to every field:

- If only one side changed the field since `base`, that change wins.
- If both sides changed it to the same value, there is nothing to resolve.
- If both changed it to different values, it is a conflict. The backend returns `409` with each conflict's base, theirs and yours values plus the current record, and writes nothing.

Different-field edits from two people both survive. On a same-field edit, the person saving second decides. Edits from the nightly import are just "theirs", so they get the same protection as edits from another person.

**Key dates: each label is one field.** "Tender launch" moved by one person and "Financial close" moved by another are independent edits, so both are kept. If both people move "Tender launch", that is a conflict. A missing label counts as the value "none", so adding, removing and moving a date all follow the same rule. Removing a date while someone else moves it is a conflict, not a silent delete. Why labels:

- A label is how researchers name a milestone. A date's position in the list carries no meaning, because the list is sorted by date.
- Treating the whole list as one field would turn every pair of edits to different dates into a false conflict.
- Matching by index breaks as soon as someone adds or removes a date, because the positions shift and the merge pairs up the wrong dates.

The costs of this choice:

- Labels must be unique within a project, and both the backend and the form enforce this.
- Renaming a label is treated as removing one date and adding another.
- A typo in a label creates a separate date. The form suggests the known labels to cut down on this.

**Ambiguous 504s are checked, never blindly retried.** A `504` from the upstream on `PUT` may or may not have saved. The backend handles it this way:

1. Re-read the record.
2. If the upstream now holds exactly what we sent, the save is done.
3. Otherwise, merge again onto whatever is there and try again, up to 3 attempts. If every attempt fails, return `502`.

A save that already landed is never applied twice blindly, and a write that slipped in meanwhile is not overwritten. A client-side timeout (5 s) is handled the same way.

**One save at a time per project, with a lock in Redis** (`backend/app/locks.py`). The merge protects edits that landed *before* our read. It cannot protect a save that lands between our GET and our PUT: our PUT resends the whole record, so it silently overwrites that save. At first I accepted this gap (see "What I cut"). Measuring it changed my mind:

| `make race`: 20 editors, 2 projects, 1 instance, slow GETs and 504s on | Confirmed saves | Lost | Refused (`503`) |
|---|---|---|---|
| Without the lock (20 s run) | 531 | 70 (13.2%) | — |
| With the lock (30 s run) | 133 | **0** | 7 of 140 saves (5%) |

A 13% silent loss is too much to leave as a documented gap. It also comes entirely from our own saves racing each other, which a lock can stop. The import, which a lock cannot stop, runs once a night. So the lock fixes the part that hurts and leaves only a small gap.

How it works:

- `SET lock:project:{id} <token> NX PX 10000` is held around the whole save: the read, the merge, the PUT and the 504 re-checks. Every backend instance uses the same Redis, so saves through any instance queue up. Saves to different projects never wait for each other.
- **Renewed while held.** A worst-case save (slow GETs, 5 s timeouts, 3 attempts) can run past 30 s. A fixed TTL would either expire mid-save or leave a crashed instance's lock stuck for a long time. A background task extends the lock every TTL/3, so a long save keeps it and a crash frees it within 10 s.
- **Token-checked release and renewal** (small Lua scripts). An instance never deletes or extends a lock another instance holds.
- **A cap on waiting.** A save waits up to 10 s for the lock, then answers `503` and writes nothing. The form shows the message, and the user saves again.
- **Fails closed.** If Redis is down, saves answer `503`. A save never runs unguarded. Reads don't touch Redis, so lists and edit pages keep working.
- **One Redis node, no Redlock.** Losing that node stops saves; it never lets two through at once. That trade is right for an internal editor.

What it costs:

- **Saves are slower under contention.** They now queue per project, and each one includes the upstream's ~2 s slow GETs and the 504 retries. With the lock, median save time was 2.1 s, p95 10 s and the slowest 12 s. With 20 people saving the same 2 projects nonstop, 5% hit the 10 s cap. Real editors save far less often.
- **A new piece of infrastructure.** Redis is added to `docker-compose.yml`, and the backend needs `REDIS_URL`.

What it does not cover:

- **Writers that skip our backend**, meaning the nightly import. It can still land between our read and our write and be overwritten. Closing this needs a version field or `If-Match` from the upstream.
- **A PUT that lands after our client gives up.** If httpx times out at 5 s, the upstream may still apply the write after we have released the lock. The mock upstream decides before it answers, so the race test cannot show this window. In production it is small but real.
- **Losing the lock mid-save.** If renewal fails (for example Redis is unreachable for longer than the TTL), the save goes on and logs a warning. The upstream has no fencing token to reject a stale write.

**Conflict UI with no default.** On a `409`, the form shows a dialog that lists each conflicting field with theirs and mine. The save button stays disabled until every field has a pick. The form is then rebuilt on top of the current record (`frontend/src/rebase.ts`, the same rule as the backend merge) and resubmitted with `base = current`. Resubmitting the old form with the new base would count every change the other person made as "mine" and silently revert it. A test covers this.

**A narrow API.** The browser sees a list summary and the editable fields. It never sees the upstream's ~15 extra fields. Linked companies are shown but not editable: the backend passes them through unchanged.

## What I cut, and why

- **The race with the nightly import.** At first I cut the whole GET→PUT race. My reasoning was that a lock in Redis covers only our three instances and never the import, so it would be a half-fix. `make race` showed the "half" it fixes is the part that loses 13% of saves, so the lock went in (above). What stays cut is the import's share of the race. Closing that needs a version field or conditional PUT from the upstream, which it doesn't have. A lock per project inside one instance was rejected outright: it would pass the single-instance race test but not protect the three instances in production.
- **User identity.** The upstream has one API key and no notion of users. The conflict dialog says "someone else", not who.
- **Editing linked companies, pagination, caching the list, live updates of an open record, and an unsaved-changes guard.** None of these are needed to show the concurrency design, and each is straightforward to add.
- **A production frontend deploy.** Vite's dev proxy routes `/api` to the backend. In production, the built bundle and `/api` would sit behind the same load balancer.

## What breaks first with 50 editors

1. **Waiting for saves on hot projects.** The Redis lock stopped lost updates (`make race`: 0 of 133 lost, down from 13%). The cost is that saves to the same project now queue. Each save holds the lock for one upstream read plus write, ~2 s when the upstream's GET is slow and more with 504 retries. With 50 editors on a few hot projects, saves wait longer and more of them hit the 10 s cap and get a `503`. This failure is **visible**, unlike the lost update it replaced. Next steps: run `make race` with `BACKEND_HOSTS` set across three instances (not done yet), retry once in the form before showing the `503`, and ask the upstream team for a version field or `If-Match`. That would let us replace the lock with a conditional PUT, which also covers the import.
2. **The list endpoint.** `GET /projects` returns every project in full, and every list view calls it. At thousands of records and 50 editors that is a lot of wide payloads. Next step: a short-TTL cache of the list summaries (staleness is fine there, since saves merge against fresh data anyway), then server-side search and pagination.
3. **Bad data from the import.** If the import writes duplicate key date labels, our per-label model rejects that record, and the edit page fails for it. Next step: decide how to show such records (read-only with a warning, or merge the duplicates).
