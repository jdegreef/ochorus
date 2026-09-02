"""Regroup Augustine's Enchiridion (Handbook on Faith, Hope, and Love) from the
124 tiny NPNF sections CCEL serves into 11 thematic chapters following the work's
own arc (Faith -> Hope -> Love). The two editor front-matter sections
(Introductory Notice, Argument) are dropped; each thematic chapter gathers its
sections as titled <h3> sub-headings, in order.

Reproducible: run `import_ccel enchiridion` first (populates the 124 raw NPNF
sections from schaff/npnf103 part iv.ii), then this script. Idempotent — it
reads the raw sections, deletes them, and writes the 11 grouped chapters.
"""
import os, sys, django
sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
django.setup()
from django.utils.html import escape
from library.ingest import clean_fragment
from library.models import Book, Chapter

# (thematic title, first raw order, last raw order) — covers raw 3..124 with no gaps
GROUPS = [
    ("The Handbook: Faith, Hope, and Love", 3, 10),
    ("Good, Evil, and Error", 11, 25),
    ("The Fall and the Grace of God", 26, 34),
    ("Christ the Mediator", 35, 43),
    ("Baptism and the Forgiveness of Sins", 44, 57),
    ("The Holy Spirit, the Church, and Pardon", 58, 68),
    ("Faith, Works, and Repentance", 69, 85),
    ("The Resurrection and the Judgment", 86, 98),
    ("The Will of God and the Two Kingdoms", 99, 115),
    ("Hope: The Lord’s Prayer", 116, 118),
    ("Love: The End of the Commandments", 119, 124),
]


def build():
    book = Book.objects.get(slug="enchiridion", language="en")
    raw = {c.order: c for c in book.chapters.all()}
    if len(raw) != 124:
        raise SystemExit(f"expected 124 raw sections, found {len(raw)} — run import_ccel enchiridion")
    # snapshot the sections we need, then clear
    sections = {o: (c.title, c.body_html) for o, c in raw.items()}
    book.chapters.all().delete()
    for i, (title, lo, hi) in enumerate(GROUPS, 1):
        parts = [
            f"<h3>{escape(sections[o][0])}</h3>{sections[o][1]}"
            for o in range(lo, hi + 1)
        ]
        body = clean_fragment("".join(parts))
        Chapter.objects.create(book=book, order=i, title=title, body_html=body)
    print(f"regrouped enchiridion: {book.chapters.count()} chapters")


if __name__ == "__main__":
    build()
