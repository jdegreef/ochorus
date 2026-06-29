#!/usr/bin/env python
"""Diagnose a book PDF's structure before/while fixing its import.

Usage (from backend/, so PyMuPDF is on the path via uv):
    uv run python ../.claude/skills/book-import/inspect_pdf.py <slug | pdf-url> [--around "text"]

Prints:
  - page count
  - font-size distribution (size -> character count): the body size is the mode;
    chapter titles are usually a larger size; running headers a slightly larger
    size that REPEATS; drop caps are very large single letters.
  - a sample of text blocks with their max font size (first pages, or the pages
    around --around "<text>" so you can see how a chapter boundary is laid out).

Use it to answer: what font size are the real chapter titles? Are there running
headers ("Chapter N" on every page)? Are drop caps separate blocks, and in order?
Then adjust the importer heuristics or add a per-book correction accordingly.
"""

from __future__ import annotations

import sys
from collections import Counter

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def resolve_pdf_url(arg: str) -> str:
    if arg.lower().endswith(".pdf"):
        return arg
    page = requests.get(f"https://ochorus.com/books/{arg}/", headers={"User-Agent": UA}, timeout=60).text
    for a in BeautifulSoup(page, "lxml").select("a[href]"):
        if a.get("href", "").lower().endswith(".pdf"):
            return a["href"]
    sys.exit(f"No PDF link found on the page for '{arg}'")


def block_text(b) -> tuple[str, float]:
    spans = [s for line in b.get("lines", []) for s in line.get("spans", [])]
    text = " ".join(" ".join(s["text"] for s in spans).split())
    size = max((s["size"] for s in spans), default=0.0)
    return text, size


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    around = None
    if "--around" in sys.argv:
        around = sys.argv[sys.argv.index("--around") + 1].lower()

    url = resolve_pdf_url(arg)
    print(f"PDF: {url}")
    data = requests.get(url, headers={"User-Agent": UA}, timeout=120).content
    doc = fitz.open(stream=data, filetype="pdf")
    print(f"pages: {doc.page_count}")

    sizes: Counter[int] = Counter()
    for page in doc:
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    sizes[round(s["size"])] += max(1, len(s["text"].strip()))
    body = sizes.most_common(1)[0][0] if sizes else 0
    print(f"\nfont sizes (size: char-count), body≈{body}:")
    for sz, n in sorted(sizes.items()):
        marker = "  <- body" if sz == body else ("  <- heading?" if sz > body else "")
        print(f"   {sz:3}: {n:>8}{marker}")

    if around:
        pages = [i for i in range(doc.page_count) if around in doc[i].get_text("text").lower()]
        pages = pages[:1] or [0]
        page_range = range(max(0, pages[0] - 1), min(doc.page_count, pages[0] + 2))
        print(f"\nblocks around {around!r} (pages {list(page_range)}):")
    else:
        page_range = range(min(5, doc.page_count))
        print("\nblocks on first pages:")
    for pi in page_range:
        for b in doc[pi].get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            t, sz = block_text(b)
            if t:
                print(f"   p{pi} sz{sz:>4.0f}: {t[:64]!r}")


if __name__ == "__main__":
    main()
