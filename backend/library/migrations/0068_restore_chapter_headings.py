"""Restore section headings the PDF import fused into prose or stranded as one.

The import lost the distinction between a heading and the paragraph under it.
Sometimes the heading was run into the first sentence ("A Fire That Must Not
Die Prayer is the heartbeat of the Church…"); sometimes it kept its own <p> and
rendered as a stubby paragraph ("Who Was He?"). Either way the structure the
author wrote was gone, in books that elsewhere in this library carry ordinary
<h2>/<h3> markup.

`data/chapter_headings.json` records where each heading is and, for translated
books, its text in every language. Nothing here is inferred: a cut is made only
where the recorded text is verified to be a literal prefix or suffix of the
paragraph that is supposed to hold it, and the paragraph count must still match
what the reviewer saw. A chapter that fails either check is left exactly as it
is — which is also why this no-ops on a database built from the corrected
fixture.

Orphans are promoted by index rather than by text: the whole paragraph IS the
heading, so there is nothing to match, and matching would have needed a string
per language that no reviewer recorded. A length guard stops a mislabelled
index from turning real prose into a heading.

`search_vector` is NULLed on rows this touches — historical models run no
save() hook, so the stored vector would stay valid-looking but stale.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent / "data" / "chapter_headings.json"
PARA = re.compile(r"<p>(.*?)</p>", re.S)
COLOPHONS = {"the end", "the end.", "end", "amen.", "amen"}
MAX_HEADING_WORDS = 12
RESTORE_LETTER = {
    ("how-to-manage-a-library", 2, 1): "L",
    ("feasting-at-the-table", 5, 1): "P",
    ("feasting-at-the-table", 6, 1): "A",
}


def _rebuild(paras, items, slug, order, lang):
    by_para = {}
    for it in items:
        if it.get("kind") == "epigraph":
            continue
        if it.get("kind") == "orphan":
            text = None
        else:
            text = (it.get("heading") or {}).get(lang)
            if text is None or text.strip().lower() in COLOPHONS:
                continue
        by_para.setdefault(it["paragraph"], []).append((it, text))
    if not by_para:
        return None

    out, changed = [], False
    for i, body in enumerate(paras, start=1):
        entries = by_para.get(i)
        if not entries:
            out.append(("p", body))
            continue
        head, tail, rest = [], [], body
        for it, text in entries:
            if it.get("kind") == "orphan":
                label = rest.strip()
                if not label or len(re.sub(r"<[^>]+>", "", label).split()) > MAX_HEADING_WORDS:
                    continue
                if label.lower() in COLOPHONS:
                    continue
                head.append(("h2", label)); rest = ""; changed = True
            elif it.get("position") == "suffix":
                if not rest.endswith(text):
                    continue
                rest = rest[: -len(text)]; tail.append(("h2", text)); changed = True
            else:
                if not rest.startswith(text):
                    continue
                rest = rest[len(text):]; head.append(("h2", text)); changed = True
        rest = rest.strip()
        letter = RESTORE_LETTER.get((slug, order, i))
        if letter and rest and rest[0].islower():
            rest = letter + rest
        out.extend(head)
        if rest:
            out.append(("p", rest))
        out.extend(tail)
    if not changed:
        return None
    return "".join(
        f"<{tag}>{(text.rstrip(':').strip() if tag == 'h2' else text).strip()}</{tag}>"
        for tag, text in out
    )


def restore(apps, schema_editor):
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
            if chapter.body_html != "".join(f"<p>{p}</p>" for p in paras):
                continue          # already restored, or not the shape we read
            if len(paras) != spec["expect"]:
                continue
            html = _rebuild(
                paras, spec["headings"], slug, chapter.order, chapter.book.language
            )
            if not html:
                continue
            chapter.body_html = html
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
            chapter.body_text = text
            chapter.word_count = len(text.split())
            chapter.search_vector = None
            chapter.save(
                update_fields=["body_html", "body_text", "word_count", "search_vector"]
            )


def noop(apps, schema_editor):
    """Deliberately irreversible — reversing would re-bury the headings."""


class Migration(migrations.Migration):
    dependencies = [("library", "0067_strip_chapter_blurbs")]
    operations = [migrations.RunPython(restore, noop)]
