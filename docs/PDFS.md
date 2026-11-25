# Where the report PDFs went

The rendered PDFs that used to sit in this folder (15 files, 8.7 MB) were
moved out of the repo on 2026-11-24, into the project's shared files under
`docs-archive/`. Every clone, CI checkout and Render build was downloading
them, and nothing in the site reads them.

Their sources stay here: the `.html` / `.md` reports and the `build_*.py`
scripts that render them. To make a PDF again, run its script and keep the
output out of git (`docs/*.pdf` is ignored).
