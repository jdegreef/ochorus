"""Bundle an Open Word Bible Balanced text (English by default) for Ochorus.

The popover, the /scripture/ pages and the notebook's daily verse quote the
Open Word Bible (OWB-B, CC0, openwordbible.org). The text ships in the repo as
`library/data/bible/owb-en-b.json.gz` so a lookup needs no network, exactly as
the bundled ASV did. This script rebuilds that file from a checkout of
https://github.com/jdegreef/open-word-bible, using that repo's own exporter
(`owb.export`) so the wording, the reader-setting defaults and the English
verse numbering are the ones its own downloads carry:

    git clone https://github.com/jdegreef/open-word-bible /tmp/owb
    uv run python scripts/build_owb_bible.py /tmp/owb
    uv run python scripts/build_owb_bible.py /tmp/owb --language am

``--language`` builds another language's Balanced text to
`library/data/bible/owb-<language>-b.json.gz`. Amharic, Swahili and Japanese
are bundled this way (founder decisions, 2026-11-18 and 2026-11-19): every work
in those languages quotes OWB, and the translation lookup resolves the Bible
ids ``owb-am``, ``owb-sw`` and ``owb-ja`` from these files
(`translation.fetch_chapter` / `fetch_verse_text`), offline. Spanish, French,
Portuguese, Hindi, Ukrainian, Vietnamese, Korean and Russian are bundled too
(2026-11-20) so a new Ochorus Original's translations quote OWB in those
languages; their classics keep the language's own Bible. Arabic (85 verses
drafted) and Luganda (none) have no OWB text yet.

Run it when the OWB text changes, review the diff of the manifest it prints,
commit. The output is byte-stable: the same OWB commit gives the same bytes.

Verse ids are pythonbible's BBBCCCVVV ints (`scripture.reference_verse_ids`).
Where OWB prints two English verses as one (1 Kings 18:33-34, Psalm 13:5-6)
the text sits under the first id and `joined` maps the others to it.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

BIBLE_DIR = Path(__file__).resolve().parents[1] / "library" / "data" / "bible"


#: Languages written without spaces between words or sentences. OWB's exporter
#: joins a verse's poetic lines with an ASCII space (right for English, Swahili,
#: Amharic), which in Japanese leaves 8,577 verses reading 「主はわたしの羊飼い。
#: わたしが…」 against the ja typography rule (no spaces after punctuation). The
#: space is layout, not wording, so it is dropped here wherever no Latin letter
#: or digit stands beside it; every character of the text is kept.
NO_SPACE_LANGUAGES = frozenset({"ja"})
_UNSPACED_JOIN = re.compile(r"(?<![A-Za-z0-9]) (?![A-Za-z0-9])")


def out_path(language: str) -> Path:
    return BIBLE_DIR / f"owb-{language}-b.json.gz"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("owb", type=Path, help="a checkout of the open-word-bible repo")
    parser.add_argument("--language", default="en", help="OWB language code (default: en)")
    args = parser.parse_args()
    OUT = out_path(args.language)
    root = args.owb.resolve()
    sys.path.insert(0, str(root))
    from owb import export, refs  # the OWB repo's own exporter

    records = [
        r
        for f in sorted(glob.glob(str(root / "content" / "*" / "*.json")))
        for r in json.loads(Path(f).read_text(encoding="utf-8"))["records"]
    ]
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    _, _, body, manifest = export.build(records, args.language, "B", fmt="json", commit=commit)

    verses: dict[str, str] = {}
    joined: dict[str, str] = {}
    for book in json.loads(body)["books"]:
        number = refs.BOOK_CODES.index(book["code"]) + 1
        for chapter in book["chapters"]:
            for v in chapter["verses"]:
                first = number * 1_000_000 + chapter["chapter"] * 1000 + v["verse"]
                text = v["text"]
                if args.language in NO_SPACE_LANGUAGES:
                    text = _UNSPACED_JOIN.sub("", text)
                verses[str(first)] = text
                if "to" in v:
                    others = [
                        number * 1_000_000 + chapter["chapter"] * 1000 + n
                        for n in range(v["verse"] + 1, v["to"] + 1)
                    ]
                else:
                    others = []
                    for held in v.get("holds", [])[1:]:
                        _, c, n = held.split(".")
                        others.append(number * 1_000_000 + int(c) * 1000 + int(n))
                for vid in others:
                    joined[str(vid)] = str(first)

    meta = {
        k: manifest[k]
        for k in ("title", "edition", "level_name", "settings", "status", "licence", "url", "commit")
    }
    data = {"meta": meta, "verses": verses, "joined": joined}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
        gz.write(raw)
    print(json.dumps({**meta, "verses": len(verses), "joined": len(joined)}, indent=1))
    print(f"wrote {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")


if __name__ == "__main__":
    main()
