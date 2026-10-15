#!/usr/bin/env python3
"""PreToolUse hook for Bash: block shell commands that would modify upstream/.

The upstream records API is owned by another team and must never be changed.
Shell can't be parsed reliably, so this is a heuristic: if a command refers to
upstream/ (or runs from inside it) and contains a file-mutating operation, it is
blocked. Reading and running upstream (`cat`, `grep`, `uv run upstream`,
`uv run pytest`) stays allowed.
"""
import json
import os
import re
import sys

MUTATIONS = [
    # Output redirection to a file (not >&2, not /dev/null).
    (r"(?<![<>&])>>?(?!&)\s*(?!/dev/null\b)[^\s&|;]", "output redirection"),
    (r"(^|[\s;&|(`])(rm|rmdir|mv|cp|touch|mkdir|tee|truncate|chmod|chown|ln|install|patch|dd|unlink)\b", "file-modifying command"),
    (r"\b(sed|perl|ruby)\b[^;&|]*\s-[a-zA-Z]*i", "in-place edit"),
    (r"\bfind\b[^;&|]*\s-(delete|exec|execdir)\b", "find -delete/-exec"),
    (r"\buv\s+(add|remove|lock|pip|init)\b", "uv dependency change"),
    (r"\buv\b[^;&|]*\s(--upgrade|--upgrade-package|-U)\b", "uv upgrade"),
    (r"\bruff\s+format\b|\bruff\b[^;&|]*--fix\b|\b(black|isort|autopep8|autoflake)\b|\bprettier\b[^;&|]*--write\b", "formatter/auto-fix"),
    (r"\bgit\s+(checkout|restore|reset|clean|rm|mv|apply|am|stash|revert|cherry-pick)\b", "git operation that rewrites files"),
]


def main() -> int:
    data = json.load(sys.stdin)
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    upstream = os.path.realpath(os.path.join(project_dir, "upstream"))
    cwd = os.path.realpath(data.get("cwd") or os.getcwd())

    in_upstream = cwd == upstream or cwd.startswith(upstream + os.sep)
    mentions_upstream = in_upstream or re.search(r"(?<![\w-])upstream(?![\w-])", command)
    if not mentions_upstream:
        return 0

    for pattern, label in MUTATIONS:
        if re.search(pattern, command):
            print(
                f"Blocked ({label}): this command appears to modify upstream/. "
                "The upstream API must never be changed (see CLAUDE.md). "
                "Work around it in the backend instead. If this is a false positive "
                "(the command only reads or runs upstream), ask the user to run it.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
