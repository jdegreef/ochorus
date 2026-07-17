# Ochorus — session notes for Claude

## Shorthands

- **"pq"** = "process the translation queue" — run the
  `.claude/skills/translation-worker` skill exactly as if the user had typed
  the full phrase (one job per run, end to end).

## Working agreements

- All dev work happens on the session's designated `claude/ochorus-dev-*`
  branch; one PR per feature, squash-merged when CI is green ("merge when CI
  passes" is a standing instruction).
- Translations always ship `source_type=ai_unreviewed`; only the user promotes
  them via `approve_translation`.
