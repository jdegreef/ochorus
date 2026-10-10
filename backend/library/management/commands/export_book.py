"""Export a book edition as EPUB, print HTML, or PDF.

    uv run python manage.py export_book the-secret-of-guidance --format pdf
    uv run python manage.py export_book the-secret-of-guidance --format epub --out /tmp/b.epub
    uv run python manage.py export_book --all --format epub --out /tmp/epubs   # every exportable EPUB (CI's epubcheck)
    uv run python manage.py export_book --all --format pdf --out /tmp/pdfs     # every stored PDF (book-pdfs.yml)

PDF is printed by headless Chrome from the print HTML (see
``library/book_export.py`` for why it is built off-server). The default PDF
output is ``frontend/static/pdfs/<slug>.pdf`` — the path ``Book.pdf_url`` points
at — so a regenerated file lands where the reader already links to it.
Set ``CHROME_PATH`` if Chrome isn't in the usual macOS/Linux place.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library import book_export
from library.export_policy import EXPORT_EDITIONS, STORED_PDF_EDITIONS, is_exportable
from library.models import Book

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def _chrome() -> str:
    for candidate in [os.environ.get("CHROME_PATH", ""), *_CHROME_CANDIDATES]:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return candidate
    raise CommandError("Chrome not found; set CHROME_PATH.")


def _print(page: Path, pdf: Path) -> None:
    subprocess.run(
        [
            _chrome(), "--headless=new", "--disable-gpu",
            "--no-pdf-header-footer", "--virtual-time-budget=15000",
            f"--print-to-pdf={pdf.resolve()}", page.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )


def _anchor_pages(pdf: Path) -> dict[str, int]:
    """Each contents anchor's 1-based page, as the footer numbers it."""
    from pypdf import PdfReader  # dev-only dependency; this command runs off-server

    reader = PdfReader(pdf)
    return {
        name.lstrip("/"): reader.get_destination_page_number(dest) + 1
        for name, dest in reader.named_destinations.items()
    }


_STATIC_PDFS = Path(settings.BASE_DIR).parent / "frontend" / "static" / "pdfs"


def _write_print_html(edition, folder: Path, pages=None) -> Path:
    """The print page (its cover and fonts) in ``folder``; returns the page path."""
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copytree(book_export.PRINT_FONTS, folder / "fonts", dirs_exist_ok=True)
    cover_src = None
    if edition.cover:
        cover_src = f"cover{edition.cover.ext}"
        (folder / cover_src).write_bytes(edition.cover.data)
    for rel, image in edition.images.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_bytes(image.data)
    page = folder / "book.html"
    page.write_text(
        book_export.render_print_html(edition, cover_src, pages), encoding="utf-8"
    )
    return page


def _print_pdf(edition, path: Path) -> None:
    """The contents page numbers need a print to know: print, read where each
    anchor landed from Chrome's named destinations, print again with them.
    Filling the numbers in can itself move a page (a long contents that tips
    onto another page), so repeat until a print agrees with its numbers.

    Printed in a scratch folder and moved to ``path`` only once it passes, so
    ``path`` never holds a half-made or failed PDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "book.pdf"
        _print(_write_print_html(edition, Path(tmp)), pdf)
        pages = _anchor_pages(pdf)
        for _ in range(3):
            _print(_write_print_html(edition, Path(tmp), pages), pdf)
            landed = _anchor_pages(pdf)
            if landed == pages:
                break
            pages = landed
        else:
            raise CommandError(f"{path.name}: contents page numbers never settled.")
        _check_author_page(edition, path.name, landed)
        _repack(pdf)
        shutil.move(pdf, path)


class AuthorPageOverflow(CommandError):
    pass


def _check_author_page(edition, name: str, pages: dict[str, int]) -> None:
    """About the Author is ONE page: its first and last lines (the print page's
    ``author-top`` / ``author-end`` anchors) must land on the same page — a bio
    too long for it pushes the end onto the next."""
    if "author-top" in pages and pages["author-top"] != pages.get("author-end"):
        raise AuthorPageOverflow(
            f"{name}: About the Author runs past one page — shorten "
            f"library/export_bios/{edition.book.author.slug}.{edition.lang}.txt."
        )


def _repack(pdf: Path) -> None:
    """Losslessly rewrite Chrome's PDF with objects packed into compressed
    object streams — about a fifth smaller, nothing on the page changes."""
    import pikepdf  # dev-only dependency; this command runs off-server

    with pikepdf.open(pdf, allow_overwriting_input=True) as doc:
        doc.save(
            pdf,
            compress_streams=True,
            recompress_flate=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )


def _bundle_cover(book, stdout) -> None:
    """Refresh the committed copy of the edition's cover (see
    ``book_export.BUNDLED_COVERS``) from the file the site serves, so every
    export also leaves the API image a cover it can use without the network."""
    dest = book_export.bundled_cover_path(book)
    if dest is None:
        return
    src = book_export.site_cover_file(book)
    if not src.is_file():
        raise CommandError(f"No cover file at {src} to bundle for the export.")
    if dest.is_file() and dest.read_bytes() == src.read_bytes():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    stdout.write(f"Bundled cover {dest.name}")


class Command(BaseCommand):
    help = "Export a book edition as EPUB, print HTML, or PDF."

    def add_arguments(self, parser):
        parser.add_argument("slug", nargs="?")
        parser.add_argument(
            "--all", action="store_true",
            help="Write every exportable EPUB (--format epub) or every stored PDF "
            "(--format pdf; export_policy.STORED_PDF_EDITIONS) into the --out folder.",
        )
        parser.add_argument(
            "--editions", default="",
            help="With --all: only these, as slug:lang,slug:lang (others in the list are skipped).",
        )
        parser.add_argument("--language", default="en")
        parser.add_argument("--format", choices=["epub", "html", "pdf"], default="pdf")
        parser.add_argument("--out", help="Output path (default depends on format).")

    def handle(self, slug, language, format, out, **options):
        if options["all"]:
            if format == "html":
                raise CommandError("--all writes epub or pdf.")
            self._all(format, Path(out or f"{format}s"), options["editions"])
            return
        if not slug:
            raise CommandError("Give a slug, or --all.")
        try:
            book = Book.objects.select_related("author").get(slug=slug, language=language)
        except Book.DoesNotExist as e:
            raise CommandError(f"No book {slug} ({language}).") from e
        if not is_exportable(book):
            raise CommandError(
                f"{slug} ({language}) is not exportable — see library/export_policy.py."
            )
        _bundle_cover(book, self.stdout)
        edition = book_export.build_edition(book)

        if format == "epub":
            path = Path(out or book_export.export_filename(book, "epub"))
            path.write_bytes(book_export.render_epub(edition))
        elif format == "html":
            path = Path(out or f"{slug}-print")
            _write_print_html(edition, path)
        else:
            path = Path(out) if out else _STATIC_PDFS / book_export.export_filename(book, "pdf")
            _print_pdf(edition, path)
        self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))

    def _all(self, format: str, folder: Path, only: str) -> None:
        """Every listed edition's file, as the API would serve it. A listed
        edition missing from the database is an error: CI seeds the fixture, so
        it means the list names a book that isn't there."""
        editions = EXPORT_EDITIONS if format == "epub" else STORED_PDF_EDITIONS
        if only:
            editions = editions & {tuple(e.split(":", 1)) for e in only.split(",") if e}
        folder.mkdir(parents=True, exist_ok=True)
        books = {
            (b.slug, b.language): b
            for b in Book.objects.select_related("author").filter(
                slug__in={slug for slug, _ in editions}, is_published=True
            )
        }
        missing = sorted(editions - books.keys())
        if missing:
            raise CommandError(f"Listed but not published: {missing}")
        jobs = [
            (book_export.build_edition(books[key]), folder / book_export.export_filename(books[key], format))
            for key in sorted(editions)
        ]
        if format == "epub":
            for edition, path in jobs:
                path.write_bytes(book_export.render_epub(edition))
        else:
            # One at a time. Parallel Chromes share the default profile and
            # collide (exit 2, or a pass laid out differently); a private
            # --user-data-dir fixes that on Linux but leaves macOS Chrome
            # hanging after it prints. A book prints in ~5 s, so it's minutes.
            # A bio too long for its page fails its own PDF, not the run: the
            # rest still print (and book-pdfs.yml still uploads them), and the
            # command fails at the end so the run goes red.
            overflowed = []
            for edition, path in jobs:
                try:
                    _print_pdf(edition, path)
                except AuthorPageOverflow as e:
                    overflowed.append(str(e))
                    continue
                self.stdout.write(f"  {path.name}")
            if overflowed:
                raise CommandError("\n".join(overflowed))
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(editions)} {format.upper()}s to {folder}"))
