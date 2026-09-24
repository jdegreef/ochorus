"""Export a book edition as EPUB, print HTML, or PDF.

    uv run python manage.py export_book the-secret-of-guidance --format pdf
    uv run python manage.py export_book the-secret-of-guidance --format epub --out /tmp/b.epub

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


class Command(BaseCommand):
    help = "Export a book edition as EPUB, print HTML, or PDF."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", default="en")
        parser.add_argument("--format", choices=["epub", "html", "pdf"], default="pdf")
        parser.add_argument("--out", help="Output path (default depends on format).")

    def handle(self, slug, language, format, out, **options):
        try:
            book = Book.objects.select_related("author").get(slug=slug, language=language)
        except Book.DoesNotExist as e:
            raise CommandError(f"No book {slug} ({language}).") from e
        if not book_export.is_exportable(book):
            raise CommandError(
                f"{slug} ({language}) is not exportable — see EXPORT_PILOT / STRINGS "
                "in library/book_export.py."
            )
        edition = book_export.build_edition(book)
        suffix = "" if language == "en" else f".{language}"

        if format == "epub":
            path = Path(out or f"{slug}{suffix}.epub")
            path.write_bytes(book_export.render_epub(edition))
        else:
            with tempfile.TemporaryDirectory() as tmp:
                cover_src = None
                if edition.cover:
                    cover_src = f"cover{edition.cover.ext}"
                    (Path(tmp) / cover_src).write_bytes(edition.cover.data)
                page = Path(tmp) / "book.html"

                def write_page(pages=None):
                    page.write_text(
                        book_export.render_print_html(edition, cover_src, pages),
                        encoding="utf-8",
                    )

                write_page()
                if format == "html":
                    path = Path(out or f"{slug}{suffix}-print")
                    shutil.copytree(tmp, path, dirs_exist_ok=True)
                else:
                    default = (
                        Path(settings.BASE_DIR).parent / "frontend" / "static" / "pdfs"
                        / f"{slug}{suffix}.pdf"
                    )
                    path = Path(out) if out else default
                    path.parent.mkdir(parents=True, exist_ok=True)
                    # Two passes for the contents page numbers (see
                    # render_print_html): print, read where each anchor landed
                    # from Chrome's named destinations, print again.
                    _print(page, path)
                    pages = _anchor_pages(path)
                    write_page(pages)
                    _print(page, path)
                    if _anchor_pages(path) != pages:
                        raise CommandError("Contents page numbers moved between passes.")
        self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))
