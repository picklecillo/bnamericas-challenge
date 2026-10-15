# CLAUDE.md

## Hard rule: never change the upstream API

Everything under `upstream/` is the **upstream records API**, owned by another team. Treat it as read-only.

- Never edit, create, delete, rename, or reformat any file under `upstream/` (code, tests, `pyproject.toml`, `uv.lock`, README, seed data).
- Never run commands that modify it: no `uv add`/`uv lock`/`uv sync --upgrade` inside `upstream/`, no formatters or linters with auto-fix pointed at it, no git operations that rewrite its contents.
- Its awkward behavior (documented in `upstream/README.md`) is part of the task. Work around it in our backend, never by patching upstream.
- If a task seems to require an upstream change, stop and ask instead of making it.

Reading `upstream/` and running it locally (per `upstream/README.md`) is fine.
