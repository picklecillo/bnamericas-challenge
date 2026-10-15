# AI trail

How I used AI on this challenge. The session logs in this folder record each prompt, what Claude Code (Opus 5.5) did, and how it was verified:

| Session | Work |
|---|---|
| [01](session-01-upstream-guardrails.md) | Guardrails so the AI can't modify `upstream/`: `CLAUDE.md` rule, plus edit and shell hooks |
| [02](session-02-backend.md) | FastAPI backend: three-way merge, safe saves, 504 handling |
| [03](session-03-frontend.md) | React + MUI frontend: list, edit form, conflict dialog |
| [04](session-04-docker-makefile.md) | Docker Compose and Makefile for local development |
| [05](session-05-decisions-readme.md) | `DECISIONS.md` and README |
| [06](session-06-locust-race-detector.md) | Locust race detector: measures lost updates in the save path |

## Tooling setup

- **Global (`~/.claude`)**, carried over from my day-to-day work. The one that shaped this task most is the `tdd` skill: red-green-refactor, one failing test at a time. Others available: `grill-me`, `tidy-first`, `prd-to-plan` and more, plus plugins for terse output, frontend design and live library docs (context7).
- **For this repo**, set up before any feature code (session 01):
  - A `CLAUDE.md` hard rule: never change `upstream/`.
  - Two `PreToolUse` hooks that enforce it: one blocks file edits under `upstream/`, the other blocks shell commands that would write there.
  - The shell hook matches words, so it blocked a few harmless commands, such as a commit message mentioning `upstream/`. Each time, Claude switched to a different tool instead of weakening the rule. The cases are noted in the logs.

## How I approached it before any code

1. Read the challenge brief and the upstream's README.
2. Drew the design on paper: browser → our backend → upstream, the three backend instances, the nightly import, and where concurrent edits collide.
3. Talked through concurrent edits and merging conflicts with Claude before writing anything: what can be known with an upstream that keeps no versions, and what a merge has to do.

## Where the tool carried the work, and where I decided

Before each coding step I asked Claude to raise clarifying questions. Its proposals came with options. The decisions were mine:

- **What "the same field" means for key dates:** each label is one field (session 02).
- **How the GET→PUT race across instances is handled:** accept it and document it, no distributed lock (session 02).
- **Linked companies:** pass-through only, not editable (session 02).
- **How a conflict is resolved in the UI:** an explicit theirs/mine pick per field, with no default (session 03).
- **Key date labels, layout and test scope for the frontend** (session 03).

From there Claude carried the implementation, following the global TDD skill: a failing test first, then the minimal code to pass. The build-log tables in sessions 02 and 03 record each red → green step. It also handled the scaffolding, the Docker setup, and the first drafts of `DECISIONS.md` and the README.

**Where I overrode it:** Claude's default is to branch before committing on `main`. In session 01 it did that, and I had it commit on `main` instead from then on. Most of my steering happened up front, in answering its questions, rather than by correcting what it produced.

## What I checked by hand

- **The UI, by hand in the browser:** list, edit, save, and the conflict flow.
- **What Claude checked and recorded in the logs:**
  - Smoke tests against the real upstream with its slow GETs and 504s turned on.
  - A deliberately broken retry, to make sure the concurrency tests weren't passing vacuously.
  - A check of the duplicate-label failure mode before claiming it in `DECISIONS.md`.
  - The test suites run inside the containers.
  - A Locust race detector against the running stack, which measured about 10–15% lost updates on a single backend instance (session 06).
