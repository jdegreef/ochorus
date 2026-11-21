#!/usr/bin/env bash
# Format (or --check) ONLY the files this branch changes — never the whole repo.
#
# Most of the repo predates its formatters (2026-11: ~680 frontend files fail
# prettier, ~400 backend files fail `ruff format`). A repo-wide sweep would
# conflict with every in-flight parallel session, so files converge as they are
# touched instead: CI checks the files a PR changes, and this script formats
# exactly those.
#
#   scripts/format-changed.sh                 # format changed files (frontend + backend)
#   scripts/format-changed.sh --check         # what CI runs; exit 1 if any would change
#   scripts/format-changed.sh frontend        # only one side (frontend | backend)
#   scripts/format-changed.sh --base HEAD^1   # diff against another ref (default origin/main)
#
# "Changed" = added/copied/modified/renamed since the merge base with --base, plus
# (when not --check) uncommitted and untracked files. Deleted files are skipped.
# Exclusions live in the tools' own config (frontend/.prettierignore,
# [tool.ruff.format] exclude in backend/pyproject.toml), so a direct
# `npx prettier` / `ruff format` agrees with this script.
#
# If a file you changed was not formatted before, formatting it rewrites more
# than your edit: commit that reformat ON ITS OWN first ("Format <file>"), then
# your real change, so a reviewer can read the change.
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"

check=
base=origin/main
sides=()
while [ $# -gt 0 ]; do
	case "$1" in
		--check) check=1 ;;
		--base) base=$2; shift ;;
		frontend|backend) sides+=("$1") ;;
		-h|--help) sed -n '2,24p' "$0"; exit 0 ;;
		*) echo "format-changed: unknown argument: $1" >&2; exit 2 ;;
	esac
	shift
done
[ ${#sides[@]} -gt 0 ] || sides=(frontend backend)

changed() {
	{
		git diff --name-only --diff-filter=ACMR "$base"...HEAD
		if [ -z "$check" ]; then
			git diff --name-only --diff-filter=ACMR HEAD
			git ls-files --others --exclude-standard
		fi
	} | sort -u
}
files=$(changed)

status=0
for side in "${sides[@]}"; do
	case "$side" in
		frontend)
			mapfile -t fe < <(printf '%s\n' "$files" | grep -E '^frontend/.*\.(ts|js|mjs|cjs|svelte|css)$' | sed 's#^frontend/##' || true)
			[ ${#fe[@]} -gt 0 ] || { echo "prettier: no changed frontend files"; continue; }
			prettier=frontend/node_modules/.bin/prettier
			[ -x "$prettier" ] || { echo "format-changed: $prettier missing — run 'npm ci' in frontend/" >&2; exit 2; }
			# --ignore-unknown + .prettierignore: ignored/generated files are skipped silently.
			if [ -n "$check" ]; then
				(cd frontend && node_modules/.bin/prettier --check --ignore-unknown "${fe[@]}") || status=1
			else
				(cd frontend && node_modules/.bin/prettier --write --ignore-unknown --log-level warn "${fe[@]}")
				echo "prettier: formatted ${#fe[@]} changed file(s)"
			fi
			;;
		backend)
			mapfile -t be < <(printf '%s\n' "$files" | grep -E '^backend/.*\.py$' | sed 's#^backend/##' || true)
			[ ${#be[@]} -gt 0 ] || { echo "ruff format: no changed backend files"; continue; }
			if [ -x backend/.venv/bin/ruff ]; then ruff=(.venv/bin/ruff)
			elif command -v uv >/dev/null; then ruff=(uv run ruff)
			else ruff=(ruff); fi
			# --force-exclude: honour pyproject's excludes (migrations, generated
			# modules) even though the paths are named explicitly.
			if [ -n "$check" ]; then
				(cd backend && "${ruff[@]}" format --check --force-exclude "${be[@]}") || status=1
			else
				(cd backend && "${ruff[@]}" format --force-exclude "${be[@]}")
			fi
			;;
	esac
done

if [ $status -ne 0 ]; then
	echo
	echo "Format the files you changed:  scripts/format-changed.sh"
	echo "(If a file was unformatted before your PR, commit its reformat separately from your change.)"
fi
exit $status
