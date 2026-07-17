"""Ship the 2026-07 content-QA repairs to the live library (prod is never
re-seeded from the fixture, so stored rows need a data migration).

1. In-place body corrections — dropped end-of-chapter full stops and hyphens
   standing in for em-dashes (the-inner-chamber ch5/ch25, the-unselfishness-of-
   god ch22) and a section heading fused into the body (the-body-of-christ-teens
   ch1). These are recorded in library.corrections.BODY_CORRECTIONS and applied
   with the same helper the importers use, so this migration and future imports
   produce identical text. Idempotent.

2. things-as-they-are ch2 ("Preface") front-matter cleanup — the extraction
   glued three front-matter sections into one chapter: the real Foreword, an
   "Illustrations" plate-list (captions for images the ebook doesn't contain),
   a Glossary whose term/definition boundaries lost their spaces, and a leaked
   title-page block. Keep the Foreword, drop the plate-list and title-page, and
   rebuild the Glossary as a clean list — its definitions are lifted verbatim
   from the stored text (only the formatting is repaired). Guarded and
   idempotent: a no-op once the chapter is already clean (e.g. a fresh install
   seeded from the regenerated fixture).

Word counts and body_text are re-derived for every touched row.
"""

from django.db import migrations

# Ordered glossary terms exactly as they appear jammed against their definitions
# in the stored text; used to split "TermDefinition" back apart verbatim.
GLOSSARY_TERMS = [
    "Agni", "Aiyo", "Ammā", "Ammāl", "Anna", "Areca Nut", "Betel", "Bandy",
    "Brahma", "Brahman", "Bramo Samâj", "Chee!", "Compound", "Coolie", "Curry",
    "Fakeer", "Guru", "Iyer", "Paddy", "Pariah", "Pūjah", "Rupee", "Saivite",
    "Salaam", "Seeley", "Shanar", "Siva", "Tom-Tom", "Vaishnavite", "Vellalar",
    "Vishnu",
]

ILLUS_MARKER = "<hr/><h3>Illustrations</h3>"
GLOSS_HEAD = "<h3>Glossary</h3>"


def _rebuild_things_as_they_are_preface(body_html):
    """Return the cleaned Preface HTML, or None if it doesn't need cleaning."""
    if ILLUS_MARKER not in body_html or GLOSS_HEAD not in body_html:
        return None
    head = body_html[: body_html.find(ILLUS_MARKER)]
    head = head.replace("</p> EUGENE STOCK.<br/> ", "</p><p>— Eugene Stock</p>")

    g0 = body_html.find(GLOSS_HEAD) + len(GLOSS_HEAD)
    g1 = body_html.find("<hr/>", g0)
    graw = body_html[g0:g1] if g1 != -1 else body_html[g0:]

    entries = []
    cursor = 0
    for i, term in enumerate(GLOSSARY_TERMS):
        pos = graw.find(term, cursor)
        if pos == -1:
            return None  # stored text unexpectedly differs — leave it untouched
        defstart = pos + len(term)
        nxt = (
            graw.find(GLOSSARY_TERMS[i + 1], defstart)
            if i + 1 < len(GLOSSARY_TERMS)
            else len(graw)
        )
        entries.append((term, graw[defstart:nxt].strip()))
        cursor = nxt

    glossary = GLOSS_HEAD + "".join(
        f"<p><i>{term}</i> — {definition}</p>" for term, definition in entries
    )
    return head + glossary


def apply(apps, schema_editor):
    from library.corrections import BODY_CORRECTIONS, apply_body_corrections
    from library.ingest import strip_trailing_pagenum
    from library.text import html_to_text

    Chapter = apps.get_model("library", "Chapter")

    for chapter in Chapter.objects.select_related("book").iterator(chunk_size=100):
        slug = chapter.book.slug
        new = strip_trailing_pagenum(chapter.body_html)
        if slug in BODY_CORRECTIONS:
            new = apply_body_corrections(slug, chapter.order, new)
        if slug == "things-as-they-are" and chapter.order == 2:
            rebuilt = _rebuild_things_as_they_are_preface(new)
            if rebuilt is not None:
                new = rebuilt
        if new != chapter.body_html:
            chapter.body_html = new
            chapter.body_text = html_to_text(new)
            chapter.word_count = len(chapter.body_text.split())
            chapter.save(update_fields=["body_html", "body_text", "word_count"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0038_merge_20260717_0338"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
