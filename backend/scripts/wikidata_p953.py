#!/usr/bin/env python
"""Write a QuickStatements batch that lists each Ochorus edition on Wikidata.

Wikidata's P953 ("full work available at URL") exists for exactly this: a link
from a WORK's item to a place its full text can be read free. This script
writes one P953 statement per published, public-domain Ochorus edition of a
work we have matched to its Wikidata item, qualified with

    P407  language of work or name   (the edition's language, as its item)
    P1476 title                      (the edition's title, in that language)

It does NOT edit Wikidata. It prints a QuickStatements v1 batch for the
founder to review and submit by hand — see docs/wikidata.md.

    uv run python scripts/wikidata_p953.py                 # batch to stdout
    uv run python scripts/wikidata_p953.py --check-live    # only URLs that answer 200
    uv run python scripts/wikidata_p953.py --unmapped      # works still missing a QID

What goes in, and what stays out:

- Works come from the content fixture (library/fixtures/content/books/), never
  a database: the fixture is what deploys.
- Only public-domain works (`library.rights.is_public_domain`, judged on the
  English edition, as the reader's JSON-LD is). That leaves out the Ochorus
  Originals and anything shared by permission.
- Only the work itself: no young-reader retelling (`-children` / `-teens`, a
  separate book of the house's, not an edition of the work) and no Modern
  English edition (the house's modernization).
- Only works matched in scripts/wikidata_works.json (slug -> QID of the WORK,
  never an edition or a translation item). An empty or missing QID is skipped.
- Only languages whose pages are live: by default the editions' own rows, and
  with --check-live each URL is fetched and kept only on HTTP 200 (a page that
  missed the build answers 404 now that there is no catch-all).
- One URL per language edition. Nothing promotional: no description, no
  "content deliverer", no reference to Ochorus beyond the URL itself.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import django

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault(
    "DJANGO_DEBUG", "true"
)  # a local tool: no secrets, no database reads
django.setup()  # library.rights imports the models; it reads no rows for an English edition

from library.rights import is_public_domain  # noqa: E402

CONTENT = BACKEND / "library" / "fixtures" / "content"
MAPPING = Path(__file__).resolve().parent / "wikidata_works.json"
SITE = "https://ochorus.com"

#: Each UI language's Wikidata item (P407's value). A language with no entry
#: here is left out of the batch rather than guessed — add its QID to list it.
LANGUAGE_QIDS: dict[str, str] = {
    "en": "Q1860",  # English
    "es": "Q1321",  # Spanish
    "sw": "Q7838",  # Swahili
    "lg": "Q33368",  # Luganda
    "pt": "Q5146",  # Portuguese
    "ar": "Q13955",  # Arabic
    "hi": "Q1568",  # Hindi
    "uk": "Q8798",  # Ukrainian
    "fr": "Q150",  # French
    "am": "Q28244",  # Amharic
    "vi": "Q9199",  # Vietnamese
    "ko": "Q9176",  # Korean
    "ja": "Q5287",  # Japanese
    "ru": "Q7737",  # Russian
}

#: Slug suffixes of the house's young-reader retellings (CLAUDE.md: the slug
#: convention IS the link to the full text) — not editions of the work.
YOUNG_READER_SUFFIXES = ("-children", "-teens")


@dataclass(frozen=True)
class Edition:
    slug: str
    language: str
    title: str

    @property
    def url(self) -> str:
        prefix = "" if self.language == "en" else f"/{self.language}"
        return f"{SITE}{prefix}/books/{self.slug}/"


def _first_row(path: Path) -> dict | None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return rows[0] if rows and rows[0].get("model") == "library.book" else None


def load_editions(content: Path = CONTENT) -> dict[str, list[Edition]]:
    """Published, public-domain editions of each work in the fixture, by slug."""
    authors = {
        a["fields"]["slug"]: a["fields"]
        for a in json.loads((content / "authors.json").read_text(encoding="utf-8"))
    }
    rows: dict[str, list[dict]] = {}
    for path in sorted((content / "books").glob("*.json")):
        row = _first_row(path)
        if row is None:
            continue
        f = row["fields"]
        rows.setdefault(f["slug"], []).append(f)

    works: dict[str, list[Edition]] = {}
    for slug, editions in sorted(rows.items()):
        if slug.endswith(YOUNG_READER_SUFFIXES):
            continue
        english = next((f for f in editions if f["language"] == "en"), None)
        if english is None:
            continue  # the rule judges a work by its English edition
        author = authors.get(english["author"][0], {})
        book = SimpleNamespace(
            language="en",
            source_type=english.get("source_type", ""),
            attribution=english.get("attribution", ""),
            author=SimpleNamespace(
                slug=english["author"][0], death_year=author.get("death_year")
            ),
        )
        if not is_public_domain(book):
            continue
        live = [
            Edition(slug, f["language"], f["title"])
            for f in editions
            if f.get("is_published", True) and f["language"] in LANGUAGE_QIDS
        ]
        if live:
            works[slug] = sorted(live, key=lambda e: (e.language != "en", e.language))
    return works


def load_mapping(path: Path = MAPPING) -> dict[str, str]:
    """slug -> work QID, skipping the comment key and blank entries."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        k: v.strip()
        for k, v in data.items()
        if not k.startswith("_") and v and v.strip()
    }


def _quoted(text: str) -> str | None:
    """A QuickStatements v1 string. v1 has no escape for a double quote or a
    tab, so a value carrying one is left out rather than mangled."""
    text = " ".join(text.split())
    return None if '"' in text or "\t" in text else f'"{text}"'


def statement(qid: str, edition: Edition) -> str:
    """One P953 line: the URL, its language and (where it can be written) its title."""
    parts = [qid, "P953", f'"{edition.url}"', "P407", LANGUAGE_QIDS[edition.language]]
    title = _quoted(edition.title)
    if title:
        parts += ["P1476", f"{edition.language}:{title}"]
    return "\t".join(parts)


def batch(
    works: dict[str, list[Edition]], mapping: dict[str, str], keep=lambda url: True
) -> list[str]:
    """Every statement, work by work in slug order, one per language edition."""
    lines = []
    for slug, editions in works.items():
        qid = mapping.get(slug)
        if not qid:
            continue
        if not (qid.startswith("Q") and qid[1:].isdigit()):
            raise ValueError(f"{slug}: {qid!r} is not a Wikidata item id")
        lines += [statement(qid, e) for e in editions if keep(e.url)]
    return lines


def answers_200(url: str) -> bool:
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "ochorus-wikidata-p953"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check-live", action="store_true", help="keep only URLs that answer HTTP 200"
    )
    parser.add_argument(
        "--unmapped", action="store_true", help="list eligible works with no QID yet"
    )
    parser.add_argument("--only", nargs="*", default=None, help="limit to these slugs")
    args = parser.parse_args(argv)

    works = load_editions()
    if args.only:
        works = {s: e for s, e in works.items() if s in args.only}
    mapping = load_mapping()
    if args.unmapped:
        for slug, editions in works.items():
            if slug not in mapping:
                print(
                    f"{slug}\t{editions[0].title}\t{','.join(e.language for e in editions)}"
                )
        return 0
    lines = batch(
        works, mapping, answers_200 if args.check_live else (lambda url: True)
    )
    print("\n".join(lines))
    mapped = sum(1 for s in works if s in mapping)
    print(
        f"# {len(lines)} statements for {mapped} of {len(works)} eligible works",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
