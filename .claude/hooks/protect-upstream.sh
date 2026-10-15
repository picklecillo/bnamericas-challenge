#!/usr/bin/env bash
# PreToolUse hook: block any file-modifying tool call targeting upstream/.
# The upstream records API is owned by another team and must never be changed.
set -euo pipefail

input=$(cat)
path=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input")
[ -z "$path" ] && exit 0

project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
case "$path" in
  /*) abs="$path" ;;
  *)  abs="$(jq -r '.cwd // empty' <<<"$input")/$path" ;;
esac

# Normalize ../ and symlinks where possible.
abs=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$abs")
upstream=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$project_dir/upstream")

case "$abs/" in
  "$upstream"/*)
    echo "Blocked: $path is inside upstream/. The upstream API must never be changed (see CLAUDE.md). Work around it in the backend instead." >&2
    exit 2
    ;;
esac
exit 0
