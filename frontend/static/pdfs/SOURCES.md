# PDF sources — `static/pdfs/`

Each book's "Download PDF" links to `/pdfs/<slug>.pdf`, served from this folder.
The 33 PDFs below were previously hotlinked from the old WordPress site
(`ochorus.com/wp-content/uploads/…`), which stopped serving them when the domain
moved to the app.

**These books have `pdf_url` blanked in the fixture** (all but the one marked
✅ generated below), so no download
button renders for them — a hidden button beats one that 404s. To restore a
download: add the file here under the exact `<slug>.pdf` name (the original
WordPress filename is kept for provenance), set that book's `pdf_url` back to
`/pdfs/<slug>.pdf` in `backend/library/fixtures/content/books/<slug>.en.json`, and
commit both together. `pdf_url` is an updatable seed field, so the next deploy
picks it up.

GENERATED PDFs (by `export_book`, one per exportable edition in
`backend/library/export_policy.py`): `the-secret-of-guidance.pdf` and every edition
of Gareth Evans' five books — `<slug>.pdf` for English, `<slug>.<lang>.pdf` for a
translation. `soar-like-the-eagle.pdf` is the one surviving WordPress file; the
English *Soar Like the Eagle* now links the generated `soar-like-the-eagle-3.pdf`
instead, and the old file stays only so inbound links to it keep working.

Only `soar-like-the-eagle.pdf` and `the-secret-of-guidance.pdf` were present before
the Gareth Evans export.
The second is not the WordPress file: it is GENERATED from the live chapters by
`uv run python manage.py export_book the-secret-of-guidance --format pdf` (run with
`PUBLIC_SITE_URL=https://ochorus.com` so the colophon links resolve) — the pilot for
free EPUB/PDF downloads, see `backend/library/book_export.py`. Re-run the command
after a text fix to that book, or the PDF drifts from what the reader serves.

The original URLs below are not dead ends: `render.yaml` 301s each one to its book
page, so an inbound link or a search result lands on the work itself rather than on
the app shell. Six are omitted there because their book is unpublished — a redirect
into the not-found page would be worse than none — and are listed in a comment
beside the rules, to be added when those books go live.

| Target file (add here) | Original WordPress source |
|---|---|
| `baptism-with-the-holy-spirit.pdf` | https://ochorus.com/wp-content/uploads/2026/02/Baptism-with-the-Holy-Spirit-1.pdf |
| `clothed-with-strength-and-dignity.pdf` | https://ochorus.com/wp-content/uploads/2026/06/CLOTHED-WITH-STRENGTH-AND-DIGNITY-BY-OCHORUS-MINISTRIES.pdf |
| `feasting-at-the-table.pdf` | https://ochorus.com/wp-content/uploads/2025/08/FEASTING-AT-THE-TABLE.pdf |
| `godliness.pdf` | https://ochorus.com/wp-content/uploads/2026/07/GODLINESS-MRS.-CATHERINE-BOOTH.pdf |
| `grace-for-grace-2.pdf` | https://ochorus.com/wp-content/uploads/2025/08/Grace-For-Grace-By-Watchman-Nee-1.pdf |
| `he-holds-my-tomorrows.pdf` | https://ochorus.com/wp-content/uploads/2025/08/He-Holds-me-Tomorrows-Gareth-Evans-1.pdf |
| `humility-2.pdf` | https://ochorus.com/wp-content/uploads/2025/08/Humility-Andrew-Murray-2.pdf |
| `if.pdf` | https://ochorus.com/wp-content/uploads/2026/02/IF-Amy-Carmichael.pdf |
| `jesus-himself-2.pdf` | https://ochorus.com/wp-content/uploads/2025/08/Jesus-Himself-Andrew-Murray-2.pdf |
| `let-us-pray-2.pdf` | https://ochorus.com/wp-content/uploads/2025/08/Let-Us-Pray-WATCHMAN-NEE-1.pdf |
| `lord-teach-us-to-pray-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/Lord-Teach-Us-to-Pray-Andrew-Murray.pdf |
| `men-and-women-who-gave-everything-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/MEN-AND-WOMEN-WHO-GAVE-EVERYTHING-BY-OCHORUS-MINISTRIES.pdf |
| `men-of-prayer-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/MEN-OF-PRAYER-BY-OCHORUS.pdf |
| `men-who-moved-heaven.pdf` | https://ochorus.com/wp-content/uploads/2026/06/MEN-WHO-MOVED-HEAVEN-BY-OCHORUS-MINISTRIES.pdf |
| `men-who-tended-the-flock-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/MEN-WHO-TENDED-THE-FLOCK-BY-OCHORUS-MINISTRIES.pdf |
| `prayer-the-pulse-of-life.pdf` | https://ochorus.com/wp-content/uploads/2025/08/PRAYER-THE-PULSE-OF-LIFE.pdf |
| `purity-of-heart.pdf` | https://ochorus.com/wp-content/uploads/2026/03/Purity-of-Heart-by-William-Booth.pdf |
| `rise-up-men-of-god-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/Rise-Up-Men-of-God-by-Ochorus.pdf |
| `stepping-stones-2.pdf` | https://ochorus.com/wp-content/uploads/2025/08/Stepping-Stones-Gareth-Evans-1.pdf |
| `talks-to-the-farmer.pdf` | https://ochorus.com/wp-content/uploads/2026/03/TALKS-TO-THE-FARMER-CHARLES-SPURGEON.pdf |
| `the-body-of-christ-a-reality.pdf` | https://ochorus.com/wp-content/uploads/2025/08/The-Body-of-Christ-Watchman-Nee.pdf |
| `the-body-of-christ-teens.pdf` | https://ochorus.com/wp-content/uploads/2026/01/The-Body-of-Christ-teen-version-compilied.pdf |
| `the-christians-secret-of-a-happy-life-4.pdf` | https://ochorus.com/wp-content/uploads/2025/08/The-Christians-secret-of-a-happy-life.pdf |
| `the-god-of-all-comfort.pdf` | https://ochorus.com/wp-content/uploads/2026/04/God-of-All-Comfort-by-Hannah-Whitall-Smith.pdf |
| `the-inner-chamber.pdf` | https://ochorus.com/wp-content/uploads/2025/08/The-Inner-Chamber.pdf |
| `the-key-in-my-hand.pdf` | https://ochorus.com/wp-content/uploads/2025/08/The-Key-in-my-Hand-Gareth-Evans-1.pdf |
| `the-masters-indwelling.pdf` | https://ochorus.com/wp-content/uploads/2025/08/THE-MASTERS-INDWELLING-ANDREW-MURRAY.pdf |
| `the-normal-christian-life.pdf` | https://ochorus.com/wp-content/uploads/2025/08/The-Normal-Christian-Life-Watchman-Nee-2.pdf |
| `the-person-and-work-of-the-holy-spirit.pdf` | https://ochorus.com/wp-content/uploads/2025/09/The-Person-and-Work-of-the-Holy-Spirit-BB.pdf |
| `the-secret-of-guidance.pdf` ✅ generated | https://ochorus.com/wp-content/uploads/2025/08/The-secret-of-guidance-by-Frederick-Brotherton-Meyer-2.pdf |
| `the-unselfishness-of-god.pdf` | https://ochorus.com/wp-content/uploads/2026/06/The-Unselfishness-of-God-by-Hannah-Whitall-Smith.pdf |
| `women-who-moved-heaven-2.pdf` | https://ochorus.com/wp-content/uploads/2026/06/WOMEN-WHO-MOVED-HEAVEN-BY-OCHORUS-MINISTRIES.pdf |
