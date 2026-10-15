# Session 05: DECISIONS.md and README

Tool: Claude Code (Opus 5.5). Date: 2026-10-15.

Goal: write the two documents the brief asks for: `DECISIONS.md` (one page: what was chosen, what was cut, what breaks first with 50 editors) and a README that replaces the challenge brief.

Note on order: these happened in the same conversation as sessions 03 and 04, but not in one block. `DECISIONS.md` was written right after the frontend (session 03). The README came after Docker and the Makefile (session 04), so it could document `make up`. Both are logged here because they are the same kind of work.

---

## Prompt 1 (after session 03)

> write DECISIONS.md

### What Claude did

- Read `backend/app/upstream.py` (the 5 s client timeout is handled like a 504) and the session-01 log. The rest of the design was already in context from sessions 02–03.
- Did not ask questions. It wrote `DECISIONS.md` straight from the decisions recorded in earlier sessions:
  - **Chosen:**
    - A backend that keeps no state of its own, with the upstream as the only truth (3 instances, plus the nightly import).
    - A per-field three-way merge, so the import's edits are just "theirs".
    - Each key date label is one field. The reasons: a label is how researchers name a milestone; treating the whole list as one field gives false conflicts; matching by position breaks on add or remove. The costs: unique labels, rename means remove plus add, typos create separate dates.
    - Verify-then-retry on ambiguous 504s.
    - A conflict dialog with no default pick.
    - The frontend rebuilding the form on the current record before resubmitting, so the other person's changes aren't reverted.
  - **Cut:**
    - The race between our GET and our PUT. A Redis lock wouldn't cover the import, and closing it needs upstream support.
    - User identity, editing linked companies, pagination, caching, live updates, the unsaved-changes guard, and a production deploy.
  - **What breaks first with 50 editors**, ranked:
    1. Lost updates in the GET→PUT window. Ranked first because it is the only *silent* failure.
    2. The list endpoint returning every record in full.
    3. Bad data from the import.

### Checked by hand

- The third failure mode was a claim Claude had not tested yet: a record with duplicate key date labels breaks our models. Before reporting it, Claude validated such a record against `ProjectDetail` and got `ValidationError`. So that project's edit page fails with an error. The claim stayed in.

## Prompt 2

> commit this to main

- Committed as `717dea9`.

## Prompt 3 (after session 04)

> write the README

### What Claude did

- Read the cursos-style setup from session 04 and the commands and numbers already verified this conversation. It replaced the challenge brief with:
  - **Intro:** what the project is, the browser-never-calls-upstream rule, and the concurrency promise, with a link to `DECISIONS.md`.
  - **Start it:**
    - With Docker: the `make` targets, the three URLs, the port overrides, and how to turn off the upstream's slow GETs and 504s.
    - Without Docker: three terminals and the env vars each part reads.
  - **Tests:** commands for Docker and local runs, and what the 22 backend and 8 frontend tests cover.
  - **Layout:** one line for each important file and folder.
  - **What works / what does not:** the GET→PUT race, the duplicate-label import data, and the full list of what wasn't built.
  - **AI tooling:** `CLAUDE.md`, the protect-upstream hooks and their false positives, and a link to `ai-trail/`.
- Kept the claims to what was verified: test counts, ports, env var defaults and commands all match what ran in sessions 02–04. The UI was covered by component tests and API smoke tests, not a manual browser pass. The README doesn't claim one, and Claude told the user to add a line if they have clicked through it.

## Prompt 4

> commit to main

- Committed as `dd2ec06`.
