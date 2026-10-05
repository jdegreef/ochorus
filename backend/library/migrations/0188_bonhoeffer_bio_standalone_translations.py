"""Carry the Bonhoeffer "standalone page" rewording into REVIEWED translations.

The bio was written for an anthology of pastors ("Most of the men in this
book…", "the pastor in these pages…", "the youngest shepherd in this book…").
The English (fixture-wins) and ``migrations/data/author_bios_{es,pt,fr}`` were
reworded to stand alone, but ``seed_author_translations`` never overwrites a
``reviewed=True`` row — so an approved row would keep the anthology framing.

Unlike 0168 this does NOT replace the whole bio or re-gate the row: the change
is a founder-directed framing edit of three sentences, not a new translation.
Each old phrase is swapped for its new one only where it appears verbatim, so
an approver's other wording is untouched and ``reviewed`` is left as it is.
A phrase the approver had already reworded is skipped. Idempotent; a no-op on
a fresh DB (the seed creates the rows later from the already-edited files).
"""

from __future__ import annotations

from django.db import migrations

SLUG = "dietrich-bonhoeffer"

SUBSTITUTIONS = {
    "es": [
        (
            "La mayoría de los hombres de este libro fueron pastores por larga costumbre",
            "Muchos de los pastores de la iglesia lo fueron por larga costumbre",
        ),
        ("Es el pastor de estas páginas que calculó", "Es el pastor que calculó"),
        (
            "Es el pastor más joven de este libro, y aquel cuyo cayado se quebró antes."
            " Pero entendió algo que también sabían los que sirvieron largos años",
            "Fue un pastor joven, y su cayado se quebró pronto."
            " Pero entendió algo que también sabían los pastores que sirvieron largos años",
        ),
    ],
    "pt": [
        (
            "A maioria dos homens deste livro eram pastores por longo hábito",
            "Muitos dos pastores da igreja o foram por longo hábito",
        ),
        ("É o pastor destas páginas que calculou", "É o pastor que calculou"),
        (
            "É o pastor mais jovem deste livro, e aquele cujo cajado foi quebrado mais cedo."
            " Mas entendeu algo que os de longa data também sabiam",
            "Foi um pastor jovem, e seu cajado foi quebrado cedo."
            " Mas entendeu algo que os pastores de longa data também sabiam",
        ),
    ],
    "fr": [
        (
            "La plupart des hommes de ce livre étaient des bergers",
            "Bien des pasteurs de l’Église étaient des bergers",
        ),
        ("Il est, dans ces pages, le pasteur qui s’assit", "Il est le pasteur qui s’assit"),
        (
            "Il est le plus jeune berger de ce livre, et celui dont la houlette fut brisée"
            " le plus tôt. Mais il avait compris ce que savaient aussi ceux qui servirent"
            " longtemps",
            "Ce fut un jeune berger, et sa houlette fut brisée tôt. Mais il avait compris"
            " ce que savaient aussi les bergers qui servirent longtemps",
        ),
    ],
}


def reword(apps, schema_editor):
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    rows = AuthorTranslation.objects.filter(
        author__slug=SLUG, language__in=SUBSTITUTIONS
    )
    for tr in rows:
        html = tr.bio_html
        for old, new in SUBSTITUTIONS[tr.language]:
            html = html.replace(old, new)
        if html != tr.bio_html:
            tr.bio_html = html
            tr.save(update_fields=["bio_html", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0187_biography_portraits"),
    ]

    operations = [
        migrations.RunPython(reword, migrations.RunPython.noop),
    ]
