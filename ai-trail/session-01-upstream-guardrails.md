# Session 01: Upstream guardrails

Tool: Claude Code (Opus 5.5). Date: 2026-10-15.

Goal: stop the AI from ever changing `upstream/`. The brief says "Do not modify anything in `upstream/`."

---

## Prompt 1

> create a CLAUDE.md file stating that the upstream api must never be changed

### What Claude did

- Listed repo files and read `README.md` to see what "upstream api" referred to (`upstream/`, the records API owned by another team).
- Created `CLAUDE.md`:

```markdown
# CLAUDE.md

## Hard rule: never change the upstream API

Everything under `upstream/` is the **upstream records API**, owned by another team. Treat it as read-only.

- Never edit, create, delete, rename, or reformat any file under `upstream/` (code, tests, `pyproject.toml`, `uv.lock`, README, seed data).
- Never run commands that modify it: no `uv add`/`uv lock`/`uv sync --upgrade` inside `upstream/`, no formatters or linters with auto-fix pointed at it, no git operations that rewrite its contents.
- Its awkward behavior (documented in `upstream/README.md`) is part of the task. Work around it in our backend, never by patching upstream.
- If a task seems to require an upstream change, stop and ask instead of making it.

Reading `upstream/` and running it locally (per `upstream/README.md`) is fine.
```

### Output

> I created `CLAUDE.md` at the repo root. It says everything under `upstream/` is read-only:
>
> - **No file changes:** no edits, new files, deletes, renames or reformatting anywhere in `upstream/`, including `pyproject.toml`, `uv.lock` and the seed data.
> - **No commands that change it:** no `uv add`, `uv lock` or upgrades there, no auto-fixing formatters or linters, and no git commands that rewrite it.
> - **Work around it:** handle the upstream's odd behavior in the backend, never by patching the upstream.
> - **Ask first:** if a task seems to need an upstream change, stop and ask.
> - **Allowed:** reading the upstream code and running it locally.
>
> I haven't committed it.
>
> A `CLAUDE.md` rule is guidance, not enforcement. If you want a hard block, I can add a `PreToolUse` hook in `.claude/settings.json` that rejects `Edit` and `Write` calls on any path under `upstream/`.

---

## Prompt 2

> add the hook

### What Claude did

- Checked that `jq` and `python3` were available.
- Created `.claude/settings.json`, which registers a `PreToolUse` hook on `Edit|Write|MultiEdit|NotebookEdit`.
- Created `.claude/hooks/protect-upstream.sh` (executable). It reads the tool call's `file_path` or `notebook_path`, resolves relative paths, `../` and symlinks, and exits with code 2 (block) if the target is inside `upstream/`.
- Tested the script by piping in sample JSON:

| Input path | Result |
|---|---|
| `<repo>/upstream/records_api/main.py` | blocked (exit 2) |
| `<repo>/backend/../upstream/x.py` | blocked (exit 2) |
| `upstream/README.md` (relative, with `cwd`) | blocked (exit 2) |
| `<repo>/backend/main.py` | allowed (exit 0) |
| `<repo>/upstream_notes.md` | allowed (exit 0) |

### Output

> I added the hook. Claude's file-editing tools are now blocked from touching anything in `upstream/`.
>
> - **`.claude/settings.json`:** runs the check before every `Edit`, `Write`, `MultiEdit` and `NotebookEdit` call.
> - **`.claude/hooks/protect-upstream.sh`:** works out the real target path, including relative paths, `../` and symlinks, and blocks the call if it points into `upstream/`. Claude gets an error message pointing it to `CLAUDE.md`.
>
> I fed the script sample inputs directly. Absolute, relative and `backend/../upstream/...` paths into `upstream/` were all blocked. `backend/main.py` and `upstream_notes.md` were allowed.
>
> I didn't trigger the hook through a real `Edit` call. If the hook hadn't loaded yet, that edit would have changed an upstream file. A new session will certainly pick it up; run `/hooks` to check it's active.
>
> It doesn't stop shell commands that write to `upstream/`, like `sed -i`, `uv lock` or `>` redirects. I can add a matching check for shell commands if you want that covered too.
>
> Nothing is committed yet.

---

## Prompt 3

> write this session's prompts and outputs to a md file

### What Claude did

- Wrote this file: `ai-trail/session-01-upstream-guardrails.md`.

## Open items

- Shell commands (`Bash`) that write to `upstream/` are still unguarded.
- The hook hasn't been checked inside a live session (`/hooks`).
- Nothing committed yet.
