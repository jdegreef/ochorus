"""Remove the editorial chapter summaries the ochorus.com import brought in.

That import (33 books) prefixed many chapters with a short paragraph written
*about* the chapter — flat modern summary register, sometimes naming the author
in the third person ("In this chapter, Andrew explains…"). It rendered as
ordinary body prose inside books marked `source_type=public_domain`, so a
reader could not tell it from the author's own words. Books that came from
Gutenberg/CCEL have none of it.

Which paragraphs go is NOT decided here. Every chapter of all 26 affected books
was read and judged, and the result is `data/chapter_blurbs.json`: per chapter,
how many leading paragraphs to drop and how many the chapter had when that was
decided. The count is the guard — a chapter that no longer matches is left
alone rather than cut blind.

Dropping by index is sound across languages because every translation in this
library passes an ordered-tag-sequence gate, so paragraph N is the same
paragraph in every edition. Checked before writing this: 42 translated
editions, zero paragraph-count disagreements with their English.

`search_vector` is NULLed on every row touched. These are historical model
instances with no `save()` hook, so the stored vector would otherwise stay
valid-looking but STALE and search would go on matching text no longer on the
page. The release chain's `backfill_search_vectors` repairs NULLs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent / "data" / "chapter_blurbs.json"
PARA = re.compile(r"<p>(.*?)</p>", re.S)


def strip_blurbs(apps, schema_editor):
    plan = json.loads(DATA.read_text())
    Chapter = apps.get_model("library", "Chapter")
    for slug, chapters in plan.items():
        wanted = {int(o): v for o, v in chapters.items()}
        rows = Chapter.objects.filter(
            book__slug=slug, order__in=list(wanted)
        ).select_related("book")
        for chapter in rows:
            spec = wanted[chapter.order]
            paras = PARA.findall(chapter.body_html)
            # The fixture is fixed in the same commit, so a database built from
            # scratch arrives here already stripped and simply doesn't match.
            if len(paras) != spec["expect"]:
                continue
            kept = paras[spec["drop"]:]
            chapter.body_html = "".join(f"<p>{p}</p>" for p in kept)
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", chapter.body_html)).strip()
            chapter.body_text = text
            chapter.word_count = len(text.split())
            chapter.search_vector = None
            chapter.save(
                update_fields=["body_html", "body_text", "word_count", "search_vector"]
            )


def noop(apps, schema_editor):
    """Deliberately irreversible — there is nothing here worth putting back."""


class Migration(migrations.Migration):
    dependencies = [("library", "0066_repair_source_defects")]
    operations = [migrations.RunPython(strip_blurbs, noop)]
