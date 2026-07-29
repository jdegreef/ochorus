"""Ship the source-defect repairs found during the Portuguese translation pass
(prod is never re-seeded from the fixture, so stored rows need a data migration
— seed_books deliberately never syncs an existing book's chapters, and
seed_books likewise treats an existing Author's bio as create-only).

1. Body corrections for two books, recorded in
   ``library.corrections.BODY_CORRECTIONS`` and applied with the same helper the
   importers use, so this migration and future imports produce identical text:

   - baptism-with-the-holy-spirit (en): two OCR'd scripture references —
     "Acts 4:8:13" -> "Acts 4:8-13" (the surrounding list hyphenates its ranges)
     and "(11 Samuel 11:6)" -> "(1 Samuel 11:6)" (the Saul / Jabesh-Gilead
     passage; "11" is an OCR of the roman "I").
   - the-key-in-my-hand: "Matthew 18:19-10" -> "18:19-20" (the quoted words are
     Matt 18:20). The typo also reached the sw/lg/pt editions, so the
     replacement matches the numerals in any language. Plus two English-only
     defects: a duplicated "armor of God of God" and "God sees they as a
     sinner" -> "them".

   Prose is untouched throughout: only mechanical typos, never an editorial
   rewrite. Ambiguous defects (a duplicated sentence in the-key-in-my-hand ch5,
   a dropped interlocutor question in baptism-with-the-holy-spirit ch2) are
   deliberately left alone — adjudicating those needs the print original.

2. F. B. Meyer's short bio was factually wrong: it credited him with
   "Melbourne's Collins Street Baptist Church" (a real church, but in Melbourne,
   Australia, and not his). His work was Melbourne Hall in Leicester — as this
   author's own long-form bio_html already says. The error had propagated to the
   es/sw/lg/pt translations; those ship as files and are re-asserted by
   seed_author_translations, so only the English Author.bio needs a migration.

Word counts and body_text are re-derived for every touched chapter. Both steps
are guarded and idempotent — a no-op on a fresh install already seeded from the
corrected fixtures.
"""

from django.db import migrations

MEYER_SLUG = "frederick-brotherton-meyer"
MEYER_OLD = (
    "including Christ Church in London and Melbourne's Collins Street "
    "Baptist Church."
)
MEYER_NEW = "including Christ Church in London and Melbourne Hall in Leicester."


def apply(apps, schema_editor):
    from library.corrections import BODY_CORRECTIONS, apply_body_corrections
    from library.text import html_to_text

    Chapter = apps.get_model("library", "Chapter")
    Author = apps.get_model("library", "Author")

    slugs = {"baptism-with-the-holy-spirit", "the-key-in-my-hand"}
    for chapter in (
        Chapter.objects.select_related("book")
        .filter(book__slug__in=slugs)
        .iterator(chunk_size=100)
    ):
        slug = chapter.book.slug
        if slug not in BODY_CORRECTIONS:
            continue
        new = apply_body_corrections(slug, chapter.order, chapter.body_html)
        if new == chapter.body_html:
            continue
        chapter.body_html = new
        chapter.body_text = html_to_text(new)
        chapter.word_count = len(chapter.body_text.split())
        chapter.save(update_fields=["body_html", "body_text", "word_count"])

    author = Author.objects.filter(slug=MEYER_SLUG).first()
    if author and MEYER_OLD in (author.bio or ""):
        author.bio = author.bio.replace(MEYER_OLD, MEYER_NEW)
        author.save(update_fields=["bio"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0056_bio_translation_slash_links"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
