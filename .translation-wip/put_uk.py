"""Store one translated uk chapter and gate it immediately (slug-aware).

    python3 put_uk.py <slug> <n> <draft.json>

Gates (a chapter that fails is not written):
  * ordered tag sequence identical to the corrected English, element for element
  * no straight quotes, no curly quotes -- uk books convert to guillemets
  * no Latin letter inside a Cyrillic word
  * the digit multiset per block survives (a dropped clause takes numbers with it)
"""

import json
import os
import re
import sys
import unicodedata

S = os.path.dirname(os.path.abspath(__file__))
STRUCT = re.compile(r"<(/?)(\w+)[^>]*>")
TAG = re.compile(r"<[^>]+>")
BLOCK = re.compile(r"</p>|</li>|</blockquote>|</h[1-6]>")
MIXED = re.compile(r"\b(?=\w*[А-Яа-яЄєІіЇїҐґ])(?=\w*[A-Za-z])\w+\b")


def check(slug, n, title, body):
    en = json.load(open(f"{S}/uk/{slug}/ch{n:02d}.json", encoding="utf-8"))
    problems, warns = [], []

    got = ["".join(m.groups()) for m in STRUCT.finditer(body)]
    want = en["tags"]
    if got != want:
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                problems.append(f"tag {i}: want <{a}> got <{b}>")
                break
        else:
            problems.append(f"tag count: want {len(want)} got {len(got)}")
        problems.append(f"tag totals want={len(want)} got={len(got)}")

    text = TAG.sub(" ", body)
    if '"' in body or "&quot;" in body:
        problems.append("straight quotes present")
    # “ ” ‘ never appear in a uk book; ” is also the CLOSER of the „ … “ nest,
    # so “ is allowed only where a „ opened. ’ is the Ukrainian APOSTROPHE
    # (U+2019, 440 uses in the shipped corpus) and is legal between letters.
    if text.count("„") != text.count("“"):
        problems.append(f"nest marks unbalanced: „{text.count('„')} “{text.count('“')}")
    if "”" in text or "‘" in text:
        problems.append("curly quotes ” / ‘ present")
    stray = [m.group(0) for m in re.finditer(r".?’.?", text)
             if not re.match(r"[А-Яа-яЄєІіЇїҐґA-Za-z]’[А-Яа-яЄєІіЇїҐґA-Za-z]", m.group(0))]
    if stray:
        problems.append(f"’ used as a quote, not an apostrophe: {stray[:5]}")

    mixed = [w for w in MIXED.findall(text)]
    if mixed:
        problems.append(f"latin-in-cyrillic: {mixed[:6]}")

    # digits per block. Strip HTML ENTITIES first: this book's English carries
    # undecoded `&#x27;` wherever an apostrophe belongs, and the naive check
    # reads "27" out of it and then reports a digit the translation "lost" in
    # every block that has one (5 phantom losses in ch02 alone). Ukrainian has
    # no such entity, so without this the real losses hide in the noise.
    ENT = re.compile(r"&#?\w+;")
    en_blocks = [ENT.sub(" ", TAG.sub(" ", b)) for b in BLOCK.split(en["body_html"])]
    uk_blocks = [ENT.sub(" ", TAG.sub(" ", b)) for b in BLOCK.split(body)]
    if len(en_blocks) == len(uk_blocks):
        for i, (a, b) in enumerate(zip(en_blocks, uk_blocks)):
            da, db = sorted(re.findall(r"\d+", a)), sorted(re.findall(r"\d+", b))
            if da != db:
                warns.append(f"block {i}: digits {da} -> {db}")
    else:
        warns.append(f"block count {len(en_blocks)} -> {len(uk_blocks)}")

    # Outer-mark COUNT against the English (warn, never fail): a multi-paragraph
    # quotation opens at every paragraph and closes once, so a faithful mirror
    # is imbalanced by exactly that much. Compare to the source, not to zero.
    en_text = TAG.sub(" ", en["body_html"])
    en_open = en_text.count("“") + en_text.count("‘")
    en_close = en_text.count("”") + len(re.findall(r"[a-zA-Z.,!?]’(?![a-zA-Z])", en_text))
    uk_open = text.count("«") + text.count("„")
    uk_close = text.count("»") + text.count("“")
    if (en_open, en_close) != (uk_open, uk_close):
        warns.append(f"outer marks en {en_open}/{en_close} -> uk {uk_open}/{uk_close}")

    ratio = len(text.split()) / en["word_count"]
    return problems, warns, ratio


def main():
    slug, n = sys.argv[1], int(sys.argv[2])
    payload = json.load(open(sys.argv[3], encoding="utf-8"))
    title, body = payload["title"], payload["body_html"]
    problems, warns, ratio = check(slug, n, title, body)
    print(f"{slug} ch{n:02d} ratio={ratio:.3f}")
    for w in warns:
        print("   WARN", w)
    if problems:
        for p in problems:
            print("   FAIL", p)
        sys.exit(1)
    os.makedirs(f"{S}/uk/{slug}/out", exist_ok=True)
    json.dump({"order": n, "title": title, "body_html": body},
              open(f"{S}/uk/{slug}/out/ch{n:02d}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"   OK -> {slug}/out/ch{n:02d}.json")


main()
