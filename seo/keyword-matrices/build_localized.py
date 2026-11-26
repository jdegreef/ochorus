#!/usr/bin/env python3
"""Keyword matrices for a language that has none yet: books, authors, topics.

Writes ``books-<lang>.csv``, ``authors-<lang>.csv`` and ``topics-<lang>.csv``
beside this file, in the column layout of the ``*-localized.csv`` sheets (so
they import into the same rank tracker), for each language named:

    python3 seo/keyword-matrices/build_localized.py fr am ko vi

Read straight from the content fixtures (no Django, no database), so the rows
are exactly what the repository ships: a published book or sermon in the
language, a writer with a book, sermon or biography there, a topic shelf with
a translation there. Bible books are left out (their searches are passages,
"psaume 23", which belong to the Bible pages, not a title row), and a house
imprint gets no "author + title" or author rows.

The modifiers (``MODIFIERS``) are natural phrasings, NOT volume-validated, the
same caveat the README gives the sw/hi sheets: have a native speaker read a
sheet before its tier-1 rows go into title tags.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "backend" / "library"
CONTENT = LIB / "fixtures" / "content"
OUT = Path(__file__).resolve().parent
SITE = "https://ochorus.com"
BIBLE_SERIES = "the-bible"

#: Per language: each facet's phrase, with ``{t}`` the title (or shelf, or
#: author name) and ``{a}`` the author. (facet, tier, template) in sheet order.
MODIFIERS: dict[str, dict[str, list[tuple[str, int, str]]]] = {
    "fr": {
        "book": [
            ("Title (navigational)", 1, "{t}"),
            ("Read online", 1, "{t} lire en ligne"),
            ("PDF", 1, "{t} pdf"),
            ("Author + title", 1, "{a} {t}"),
            ("Free online", 2, "{t} gratuit"),
            ("Full text", 2, "{t} texte intégral"),
            ("Summary", 3, "{t} résumé"),
        ],
        "author": [
            ("Name (navigational)", 1, "{t}"),
            ("Biography", 1, "{t} biographie"),
            ("Who was", 2, "qui était {t}"),
            ("Books", 1, "livres de {t}"),
            ("Books free", 2, "livres de {t} gratuits"),
            ("Sermons", 2, "sermons de {t}"),
        ],
        "topic": [
            ("Theme term", 1, "{t}"),
            ("Collection", 1, "livres sur {t}"),
            ("Best-of", 2, "meilleurs livres sur {t}"),
        ],
    },
    "am": {
        "book": [
            ("Title (navigational)", 1, "{t}"),
            ("Read online", 1, "{t} በመስመር ላይ ማንበብ"),
            ("PDF", 1, "{t} pdf"),
            ("Author + title", 1, "{a} {t}"),
            ("Free online", 2, "{t} በነጻ"),
            ("Full text", 2, "{t} ሙሉ ጽሑፍ"),
            ("Summary", 3, "{t} ማጠቃለያ"),
        ],
        "author": [
            ("Name (navigational)", 1, "{t}"),
            ("Biography", 1, "{t} የሕይወት ታሪክ"),
            ("Who was", 2, "{t} ማን ነበር"),
            ("Books", 1, "{t} መጻሕፍት"),
            ("Books free", 2, "{t} መጻሕፍት በነጻ"),
            ("Sermons", 2, "{t} ስብከቶች"),
        ],
        "topic": [
            ("Theme term", 1, "{t}"),
            ("Collection", 1, "ስለ {t} መጻሕፍት"),
            ("Best-of", 2, "ስለ {t} ምርጥ መጻሕፍት"),
        ],
    },
    "ko": {
        "book": [
            ("Title (navigational)", 1, "{t}"),
            ("Read online", 1, "{t} 온라인 읽기"),
            ("PDF", 1, "{t} pdf"),
            ("Author + title", 1, "{a} {t}"),
            ("Free online", 2, "{t} 무료"),
            ("Full text", 2, "{t} 전문"),
            ("Summary", 3, "{t} 요약"),
        ],
        "author": [
            ("Name (navigational)", 1, "{t}"),
            ("Biography", 1, "{t} 전기"),
            ("Who was", 2, "{t} 누구"),
            ("Books", 1, "{t} 책"),
            ("Books free", 2, "{t} 책 무료"),
            ("Sermons", 2, "{t} 설교"),
        ],
        "topic": [
            ("Theme term", 1, "{t}"),
            ("Collection", 1, "{t}에 관한 책"),
            ("Best-of", 2, "{t} 추천 도서"),
        ],
    },
    "vi": {
        "book": [
            ("Title (navigational)", 1, "{t}"),
            ("Read online", 1, "{t} đọc online"),
            ("PDF", 1, "{t} pdf"),
            ("Author + title", 1, "{a} {t}"),
            ("Free online", 2, "{t} miễn phí"),
            ("Full text", 2, "{t} toàn văn"),
            ("Summary", 3, "{t} tóm tắt"),
        ],
        "author": [
            ("Name (navigational)", 1, "{t}"),
            ("Biography", 1, "tiểu sử {t}"),
            ("Who was", 2, "{t} là ai"),
            ("Books", 1, "sách của {t}"),
            ("Books free", 2, "sách của {t} miễn phí"),
            ("Sermons", 2, "bài giảng của {t}"),
        ],
        "topic": [
            ("Theme term", 1, "{t}"),
            ("Collection", 1, "sách về {t}"),
            ("Best-of", 2, "sách hay nhất về {t}"),
        ],
    },
}

#: Scripts with case: phrases are lowercased (the existing sheets' convention),
#: except author names, which a searcher types either way and stay as written
#: in a script with no case.
CASED = {"fr", "vi"}

#: A shelf title's own "On …" ("Về sự cầu nguyện", "기도에 관하여") is dropped
#: inside a phrase, so "books on prayer" doesn't read "books on on prayer" (the
#: es sheet's "libros sobre la oración" from "Sobre la oración"). The Theme
#: term row keeps the title as it stands.
ON_PREFIX = {"fr": ("sur ",), "vi": ("về ",)}
ON_SUFFIX = {"ko": ("에 관하여",)}


def _bare(title: str, lang: str) -> str:
    low = title.lower()
    for p in ON_PREFIX.get(lang, ()):
        if low.startswith(p):
            return title[len(p):]
    for suf in ON_SUFFIX.get(lang, ()):
        if title.endswith(suf):
            return title[: -len(suf)]
    return title


def _rows(kind: str, lang: str) -> list[dict]:
    out = []
    for path in sorted((CONTENT / kind).glob(f"*.{lang}.json")):
        row = json.loads(path.read_text(encoding="utf-8"))[0]["fields"]
        if row.get("is_published", True):
            out.append(row)
    return out


def _phrase(template: str, lang: str, **parts: str) -> str:
    text = template.format(**parts)
    return text.lower() if lang in CASED else text


def build(lang: str) -> dict[str, int]:
    mods = MODIFIERS[lang]
    authors = {
        a["fields"]["slug"]: a["fields"]
        for a in json.loads((CONTENT / "authors.json").read_text(encoding="utf-8"))
    }
    books = [b for b in _rows("books", lang) if not (b.get("series") or [None])[0] == BIBLE_SERIES]
    sermons = _rows("sermons", lang)
    bios = {p.name.split(".")[0] for p in (LIB / "migrations" / "data" / f"author_bios_{lang}").glob("*.html")}
    counts = {}

    with open(OUT / f"books-{lang}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Phrase", "Language", "Intent", "Tier", "Book (localized)", "Author", "Target URL"])
        n = 0
        for b in sorted(books, key=lambda b: b["title"].casefold()):
            author = authors.get(b["author"][0], {})
            url = f"{SITE}/{lang}/books/{b['slug']}"
            for facet, tier, tpl in mods["book"]:
                if "{a}" in tpl and author.get("is_imprint"):
                    continue
                w.writerow([_phrase(tpl, lang, t=b["title"], a=author.get("name", "")), lang, facet, tier,
                            b["title"], author.get("name", ""), url])
                n += 1
        counts["books"] = n

    with_books = {b["author"][0] for b in books}
    with_sermons = {s["author"][0] for s in sermons}
    with open(OUT / f"authors-{lang}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Phrase", "Language", "Facet", "Tier", "Author", "Target URL"])
        n = 0
        for slug in sorted(with_books | with_sermons | bios):
            a = authors.get(slug)
            if not a or a.get("is_imprint"):
                continue
            # The facets this writer's page can answer in this language (the
            # README's content gating): a biography, books, sermons.
            has = {
                "Name (navigational)": True,
                "Biography": slug in bios,
                "Who was": slug in bios,
                "Books": slug in with_books,
                "Books free": slug in with_books,
                "Sermons": slug in with_sermons,
            }
            url = f"{SITE}/{lang}/authors/{slug}"
            for facet, tier, tpl in mods["author"]:
                if has[facet]:
                    # Names stay in Latin script, as written (README convention).
                    phrase = tpl.format(t=a["name"])
                    w.writerow([phrase.lower() if lang in CASED else phrase, lang, facet, tier, a["name"], url])
                    n += 1
        counts["authors"] = n

    topics_en = _topic_titles_en()
    shelves = json.loads((LIB / "data" / "topic_translations" / f"{lang}.json").read_text(encoding="utf-8"))
    with open(OUT / f"topics-{lang}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Phrase", "Language", "Intent", "Tier", "Shelf (localized)", "Shelf (en)", "Target URL"])
        n = 0
        for slug, entry in shelves.items():
            if slug.startswith("_") or not isinstance(entry, dict) or not entry.get("title"):
                continue
            url = f"{SITE}/{lang}/topics/{slug}"
            for facet, tier, tpl in mods["topic"]:
                t = entry["title"] if facet == "Theme term" else _bare(entry["title"], lang)
                w.writerow([_phrase(tpl, lang, t=t), lang, facet, tier, entry["title"],
                            topics_en.get(slug, ""), url])
                n += 1
        counts["topics"] = n
    return counts


def _topic_titles_en() -> dict[str, str]:
    """``{slug: English title}`` from ``topic_seed.TOPICS`` (slug, title, …),
    read as text so the script needs no Django."""
    import ast

    src = (LIB / "topic_seed.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TOPICS" for t in node.targets):
            out = {}
            for elt in node.value.elts:
                if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                    slug, title = (ast.literal_eval(e) for e in elt.elts[:2])
                    out[slug] = title
            return out
    return {}


if __name__ == "__main__":
    langs = sys.argv[1:] or sorted(MODIFIERS)
    for lang in langs:
        if lang not in MODIFIERS:
            sys.exit(f"no modifiers for {lang!r}; add them to MODIFIERS first")
        print(lang, build(lang))
