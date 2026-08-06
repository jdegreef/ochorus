"""Scan the English library for the import-defect classes we keep finding.

Every check here was written from a real instance found the expensive way --
during translation, after the defect had already propagated into three to six
language editions. The point is to find the rest before that happens again.

PRECISION IS THE WHOLE GAME. A first version of this scanner reported 8,917
findings, of which the overwhelming majority were false: it flagged 17th-century
spaced punctuation as an artifact, every capitalised word beginning with I as a
fused drop cap, and "A SHORT" as broken small caps. A scanner nobody trusts is
worse than none, because its output gets skimmed. So each check below is
narrowed by a test that distinguishes the defect from the convention, and the
comment says what that test is.

Usage:  python3 scan.py [--class NAME] [--slug SLUG] [--limit N] [--json OUT]
"""
import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path

CONTENT = Path("/home/user/ochorus/backend/library/fixtures/content")
TAG = re.compile(r"<[^>]+>")
BLOCK = re.compile(r"<(p|h2|h3|h4|blockquote|li)>(.*?)</\1>", re.S)

# An anachronism is only a defect in a book its author could not have written
# it in. Gareth Evans (b. 1938) may mention television; Andrew Murray may not.
# `ochorus-originals` is house-written, so modern references are legitimate.
PD_CUTOFF = 1930


def load_authors():
    rows = json.loads((CONTENT / "authors.json").read_text())
    return {r["fields"]["slug"]: r["fields"].get("death_year") for r in rows}


def text(fragment: str) -> str:
    return html.unescape(TAG.sub(" ", fragment))


def excerpt(t: str, i: int, w: int = 65) -> str:
    return " ".join(t[max(0, i - w):i + w].split())


# --- checks ---------------------------------------------------------------

ANACHRONISM = re.compile(
    r"\b(cars?|automobiles?|internet|online|websites?|e-?mails?|smartphones?|"
    r"computers?|television|TV|social media|podcasts?|credit cards?|CEOs?)\b",
    re.I)

# The test that makes this precise: the split letters must REJOIN into a real
# word. "L ORD" -> LORD is the defect (stepping-stones-2 ch02). "A SHORT" ->
# ASHORT is not a word, so it is just a small-caps opening. That single test
# took this check from 233 findings to 8.
SMALLCAP_WORDS = {"LORD", "GOD", "JESUS", "CHRIST", "SPIRIT", "FATHER", "SON",
                  "KING", "HOLY", "AMEN", "SELAH", "ISRAEL"}
BROKEN_SMALLCAPS = re.compile(r"\b([A-Z])\s+([A-Z]{2,})\b")

# A fused drop cap is "Ithink" -> I + think. The test is that the REMAINDER is
# a common word; without it the pattern matches Indian, Inquire, Ireland, In...
FUSED_TAIL = {"think", "thank", "have", "know", "will", "want", "believe",
              "remember", "asked", "said", "went", "saw", "am", "was", "had",
              "shall", "would", "could", "should", "must", "wish", "hope",
              "love", "pray", "cannot", "never", "always", "once", "often"}
DROPCAP_FUSED = re.compile(r"\b(I)([a-z]{2,})\b")

HYPHEN_SPACE = re.compile(r"\b\w+-\s+\w+\b")
RUN_TOGETHER = re.compile(r"\b[a-z]{3,}\.[A-Z][a-z]{2,}\b")
SPACE_BEFORE_PUNCT = re.compile(r"\S\s+[,.;:!?](?:\s|$)")

MISSPELLINGS = {
    "Millenium": "Millennium", "capitol city": "capital city",
    "Stocklholm": "Stockholm", "Guatamalan": "Guatemalan",
    "Malasia": "Malaysia", "Chapultapek": "Chapultepec",
    "Brazilia": "Brasília", "Deja Vue": "déjà vu",
    "Bob Beamer": "Bob Beamon", "Nicki Cruz": "Nicky Cruz",
    "Cuidad": "Ciudad", "Heratii": "Horatii", "Te quyiero": "Te quiero",
    "selfexaltation": "self-exaltation", "allpervading": "all-pervading",
    "Weibe": "Wiebe (spelled Wiebe elsewhere in the same book)",
}


def check_block(t, is_pd):
    out = []
    if is_pd:
        for m in ANACHRONISM.finditer(t):
            out.append(("anachronism", excerpt(t, m.start())))
    for m in BROKEN_SMALLCAPS.finditer(t):
        if m.group(1) + m.group(2) in SMALLCAP_WORDS:
            out.append(("broken-smallcaps", excerpt(t, m.start())))
    for m in DROPCAP_FUSED.finditer(t):
        if m.group(2) in FUSED_TAIL:
            out.append(("dropcap-fused", excerpt(t, m.start())))
    for m in HYPHEN_SPACE.finditer(t):
        out.append(("hyphen-space", excerpt(t, m.start())))
    for m in RUN_TOGETHER.finditer(t):
        out.append(("run-together", excerpt(t, m.start())))
    for bad in MISSPELLINGS:
        i = t.find(bad)
        if i >= 0:
            out.append(("misspelling", excerpt(t, i)))
    return out


def orphan_quotes(blocks):
    """A closing quote with nothing open.

    Long quotations open every paragraph and close only the last, so an odd
    count mid-run is the convention, not a defect. What is wrong is a block
    that closes when nothing is open -- humility-2 ch09 and stepping-stones-2
    ch13 both do this, and in both the speech attribution breaks mid-sentence.
    """
    out, depth = [], 0
    for i, t in enumerate(blocks):
        opens, closes = t.count("“"), t.count("”")
        if closes > opens and depth + opens - closes < 0:
            out.append(("orphan-close-quote", i, excerpt(t, t.find("”"))))
        depth = max(0, depth + opens - closes)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="klass")
    ap.add_argument("--slug")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json")
    a = ap.parse_args()

    deaths = load_authors()
    found = defaultdict(list)
    # space-before-punct is bimodal: 777/647/586 in the 17c texts, where it is
    # the era's typography, against 1 or 2 in a modern one, where it is an
    # italics-strip artifact. Count per book first, then only report the books
    # where it is sporadic enough to be a defect rather than a convention.
    spb = defaultdict(list)

    paths = sorted(CONTENT.glob("books/*.en.json")) + sorted(CONTENT.glob("sermons/*.en.json"))
    for p in paths:
        slug = p.name[:-8]
        if a.slug and a.slug != slug:
            continue
        recs = json.loads(p.read_text())
        meta = next((r["fields"] for r in recs
                     if r["model"] in ("library.book", "library.sermon")), {})
        author = (meta.get("author") or [None])[0]
        died = deaths.get(author)
        is_pd = bool(died) and died < PD_CUTOFF

        for rec in recs:
            f = rec["fields"]
            if rec["model"] == "library.chapter":
                where = f"{slug} ch{f['order']:02d}"
            elif rec["model"] == "library.sermon":
                where = f"{slug} (sermon)"
            else:
                continue
            blocks = [text(b) for _, b in BLOCK.findall(f["body_html"])]
            for i, t in enumerate(blocks):
                for label, ex in check_block(t, is_pd):
                    found[label].append((where, i, ex))
                for m in SPACE_BEFORE_PUNCT.finditer(t):
                    spb[slug].append((where, i, excerpt(t, m.start())))
            for label, i, ex in orphan_quotes(blocks):
                found[label].append((where, i, ex))
            for m in re.finditer(r"\b([A-Za-z]+)-([a-z])\b", f.get("title", "")):
                if f"{m.group(1)}-{m.group(2).upper()}" in text(f["body_html"]):
                    found["title-case-vs-body"].append((where, -1, f["title"]))

    for slug, rows in spb.items():
        if len(rows) <= 15:
            found["space-before-punct"].extend(rows)

    total = sum(len(v) for v in found.values())
    print(f"{total} findings across {len(found)} classes\n")
    for label in sorted(found, key=lambda k: -len(found[k])):
        if a.klass and a.klass != label:
            continue
        rows = found[label]
        print(f"=== {label}  ({len(rows)})")
        for where, i, ex in rows[:a.limit or 8]:
            print(f"   {where} p{i}: {ex[:145]}")
        if not a.limit and len(rows) > 8:
            print(f"   … {len(rows) - 8} more")
        print()
    if a.json:
        Path(a.json).write_text(json.dumps(
            {k: [list(r) for r in v] for k, v in found.items()},
            ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
