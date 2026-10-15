# Decisions

## What I chose

**A stateless backend, with the upstream as the only source of truth.** Production runs three backend instances, and a nightly import writes to the upstream directly. Any version table, cache or lock held inside our backend would be wrong the moment the import runs or another instance saves. So every save reads the upstream's current record and works from that. Any instance can serve any request.

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

**Conflict UI with no default.** On a `409`, the form shows a dialog that lists each conflicting field with theirs and mine. The save button stays disabled until every field has a pick. The form is then rebuilt on top of the current record (`frontend/src/rebase.ts`, the same rule as the backend merge) and resubmitted with `base = current`. Resubmitting the old form with the new base would count every change the other person made as "mine" and silently revert it. A test covers this.

**A narrow API.** The browser sees a list summary and the editable fields. It never sees the upstream's ~15 extra fields. Linked companies are shown but not editable: the backend passes them through unchanged.

## What I cut, and why

- **The race between our GET and our PUT.** Another instance or the nightly import can write between our read and our write, and that write is lost for the fields we resend. Closing this needs either support from the upstream (versions or conditional PUT), which it doesn't have, or a distributed lock. A lock in Redis would only cover our three instances, not the import. I accepted the gap and documented it in code instead of half-fixing it.
- **User identity.** The upstream has one API key and no notion of users. The conflict dialog says "someone else", not who.
- **Editing linked companies, pagination, caching the list, live updates of an open record, and an unsaved-changes guard.** None of these are needed to show the concurrency design, and each is straightforward to add.
- **A production frontend deploy.** Vite's dev proxy routes `/api` to the backend. In production, the built bundle and `/api` would sit behind the same load balancer.

## What breaks first with 50 editors

1. **Lost updates in the GET→PUT window.** With more people on the same hot projects, two saves overlapping inside one read-then-write window becomes likely. Slow upstream GETs (~2 s), the 504 retries, and saves landing on different instances all widen the window. This is the one failure that is **silent**. Next step: ask the upstream team for a version field or `If-Match`. Short of that, re-read after each PUT to at least detect and report a clobber.
2. **The list endpoint.** `GET /projects` returns every project in full, and every list view calls it. At thousands of records and 50 editors that is a lot of wide payloads. Next step: a short-TTL cache of the list summaries (staleness is fine there, since saves merge against fresh data anyway), then server-side search and pagination.
3. **Bad data from the import.** If the import writes duplicate key date labels, our per-label model rejects that record, and the edit page fails for it. Next step: decide how to show such records (read-only with a warning, or merge the duplicates).
