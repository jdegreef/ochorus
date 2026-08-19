# migrations/data

Data files read by the deploy seeds and, historically, by data migrations.

## Why `author_bios_sw/short.json` and `author_bios_lg/short.json` exist, empty

Migration `0024_author_bios_sw_lg` opens those two files **unguarded** at
migrate time, and migrations are immutable once they have run against prod
(backend/CLAUDE.md). Deleting the files would crash `manage.py migrate` on a
fresh database. Emptying them to `{}` changes nothing that matters: on prod
the migration has already run and never re-runs, and on a fresh DB it iterates
zero entries — which is what the full file effectively produced too, because
authors are seeded *after* migrate. The one divergent case is a long-lived dev
DB that already has authors but still sits behind 0024: its `migrate` no
longer backfills the sw/lg bios at migrate time. They arrive on the next
`seed_author_translations` run instead — the same step that owns them in every
other environment.

The short bios themselves now live as per-slug `<slug>.short.txt` files beside
the `<slug>.html` long forms, read by `seed_author_translations`. Do not add
entries back to any `short.json`: nothing reads them any more, so an entry
there is a bio that silently never ships.
