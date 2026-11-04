"""Generate the two appendices of a *A Cloud of Praying Witnesses* volume.

Every volume of the series ends with the same two appendices, and neither is
written by hand, so neither can drift from the book:

- **Appendix A: Key Insights** gathers each chapter's three insights by theme,
  from the volume's data file (``volume-NN.chapters.json``). Themes come from
  the closed list ``THEMES`` below, shared by the whole series, so the final
  volume's master index can merge every volume's appendix.
- **Appendix B: Scripture Index** lists every Scripture the manuscript cites,
  in Bible order, with the chapters that cite it. It is read from the
  manuscript itself (``volume-NN.md``), not from the data file, so a verse
  added to a chapter appears in the index on the next run.

Output is ``volume-NN.appendices.md`` beside the manuscript, in the same closed
Markdown subset (``build_rooted.parse``). It is byte-stable: the same inputs
give the same bytes, so a diff after a run is a real change.

    uv run python scripts/build_praying_witnesses_appendices.py 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from library import scripture  # noqa: E402  (pythonbible only; no Django)

DATA = (
    ROOT
    / "library"
    / "management"
    / "commands"
    / "data"
    / "a-cloud-of-praying-witnesses"
)

# The series' closed theme list, in the order Appendix A prints them.
THEMES = (
    "The Father's Love",
    "Learning to Pray",
    "Making Room for Prayer",
    "Asking Boldly",
    "Persistence",
    "Faith",
    "Humility and Mercy",
    "Forgiveness",
    "Thanksgiving",
    "Guidance and Surrender",
    "Prayer in Suffering and Testing",
    "Praying Together",
    "Praying for Others",
    "Christ Who Prays for Us",
)

# A book's heading where it differs from how a citation names it.
BOOK_HEADINGS = {"Psalm": "Psalms"}

# A citation: "Book C:V", "Book C:V-V", "Book C:V, V" ("1 John 5:14", "Psalm 67:1-2").
REF = re.compile(
    r"\b((?:[1-3] )?[A-Z][a-z]+(?: of [A-Z][a-z]+)?) (\d+):(\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)"
)


def label(entry: dict) -> str:
    """How a chapter is named in an index line."""
    n = entry["chapter"]
    if n == 0:
        return "Introduction"
    if entry["title"].startswith("Conclusion"):
        return "Conclusion"
    return f"Chapter {n}, *{entry['title']}*"


def chapter_bodies(manuscript: str) -> list[str]:
    """The manuscript split at each ``## `` heading, in order (front matter dropped)."""
    return re.split(r"^## ", manuscript, flags=re.M)[1:]


def citations(body: str) -> list[tuple[str, tuple[int, ...]]]:
    """Each distinct reference a chapter cites, with its sorted verse ids."""
    seen: dict[str, tuple[int, ...]] = {}
    for book, chap, verses in REF.findall(body):
        for part in verses.split(", "):
            ref = f"{book} {chap}:{part}"
            ids = tuple(sorted(scripture.reference_verse_ids(ref)))
            if ids:  # not a Bible book ("Volume 3:2" can't occur, but be strict)
                seen.setdefault(ref, ids)
    return list(seen.items())


def appendix_a(entries: list[dict]) -> str:
    by_theme: dict[str, list[str]] = {t: [] for t in THEMES}
    for e in entries:
        for ins in e["insights"]:
            if ins["theme"] not in by_theme:
                raise SystemExit(
                    f"chapter {e['chapter']}: unknown theme {ins['theme']!r}; add it to THEMES"
                )
            by_theme[ins["theme"]].append(
                f"- **{ins['text']}** {label(e)} ({e['anchor']})"
            )
    out = [
        "## Appendix A: Key Insights",
        "",
        "Every chapter of this book closes with three key insights. Here they are "
        "gathered by theme, so you can see at a glance what Jesus teaches about each "
        "part of prayer. Each insight points back to the chapter where it is taught "
        "and to that chapter's key verse.",
    ]
    for theme in THEMES:
        if by_theme[theme]:
            out += ["", f"### {theme}", "", *by_theme[theme]]
    return "\n".join(out)


def appendix_b(entries: list[dict], bodies: list[str]) -> str:
    refs: dict[str, dict] = {}
    for e, body in zip(entries, bodies, strict=True):
        for ref, ids in citations(body):
            r = refs.setdefault(ref, {"ids": ids, "chapters": []})
            key = " (key verse)" if ref == e["anchor"] else ""
            r["chapters"].append(f"{label(e)}{key}")
    out = [
        "## Appendix B: Scripture Index",
        "",
        "Every passage of Scripture quoted or referred to in this book, in Bible "
        'order, with the chapters where it appears. "Key verse" marks the '
        "Scripture a chapter is built on.",
    ]
    book = None
    for ref, r in sorted(refs.items(), key=lambda kv: (kv[1]["ids"], kv[0])):
        name, verses = ref.rsplit(" ", 1)
        if name != book:
            book = name
            out += ["", f"### {BOOK_HEADINGS.get(name, name)}", ""]
        out.append(f"- **{verses}**: {'; '.join(r['chapters'])}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("volume", type=int)
    args = parser.parse_args()
    stem = DATA / f"volume-{args.volume:02d}"
    entries = json.loads(stem.with_suffix(".chapters.json").read_text())
    bodies = chapter_bodies(stem.with_suffix(".md").read_text())
    if len(entries) != len(bodies):
        raise SystemExit(
            f"{len(entries)} data records but {len(bodies)} chapters in the manuscript"
        )
    for e, body in zip(entries, bodies, strict=True):
        title = body.splitlines()[0].strip()
        if title != e["title"]:
            raise SystemExit(
                f"record {e['chapter']} is {e['title']!r} but the manuscript has {title!r}"
            )
    text = appendix_a(entries) + "\n\n---\n\n" + appendix_b(entries, bodies) + "\n"
    out = stem.with_suffix(".appendices.md")
    out.write_text(text)
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
