"""Internet Archive hOCR → paragraphs, using the print's own first-line indents.

The `_djvu.txt` text layer that `import_archive` reads marks a paragraph only
by a blank line, and a page break looks exactly like one — so a paragraph that
runs over a page whose last line happens to end a sentence is split in two, and
nothing in the text can tell the two apart. The page IMAGE can: a printed
paragraph opens on an indented line. Archive's `_hocr.html` keeps every line's
bounding box, so this module rebuilds paragraphs from the indents themselves,
across page breaks, and leaves only the book-specific parts (which lines are
furniture, where the chapters begin, what the OCR misread) to the caller.

Built for Sadhu Sundar Singh's *Reality and Religion* (1924) and *With and
Without Christ* (1929); see `build_reality_and_religion` and
`build_with_and_without_christ`.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass
from statistics import median

import requests

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"

_PAGE = re.compile(r"<div class=['\"]ocr_page['\"]")
_LINE = re.compile(
    r"<span class=['\"]ocr_(?:line|caption|header|textfloat)['\"][^>]*?"
    r"title=['\"]bbox (\d+) (\d+) (\d+) (\d+)[^'\"]*['\"][^>]*>(.*?)</span>\s*"
    r"(?=<span class=['\"]ocr_(?:line|caption|header|textfloat)|</p>)",
    re.S,
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
#: A line that is only a page number, a roman folio, or a printer's signature
#: mark ("I B", "5a)", "3/", "II]") — short, and no run of three lowercase
#: letters.
_FOLIO = re.compile(r"^(?!.*[a-z]{3})[\w.,'’‘|/()\[\]*•\-\s]{1,7}$")


@dataclass(frozen=True)
class Line:
    page: int
    x0: int
    y0: int
    x1: int
    y1: int
    text: str


def fetch_hocr(item_id: str) -> str:
    url = f"https://archive.org/download/{item_id}/{item_id}_hocr.html"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse(hocr: str) -> list[Line]:
    """Every text line of the scan, in reading order, tagged with its page."""
    out: list[Line] = []
    for page, chunk in enumerate(_PAGE.split(hocr)[1:]):
        for m in _LINE.finditer(chunk):
            text = _WS.sub(" ", _html.unescape(_TAG.sub("", m.group(5)))).strip()
            if text:
                x0, y0, x1, y1 = (int(v) for v in m.groups()[:4])
                out.append(Line(page, x0, y0, x1, y1, text))
    return out


def margins(lines: list[Line]) -> dict[int, int]:
    """Each page's left text margin: the median start of its full-width lines.

    Recto and verso pages sit at different offsets in the scan, so the margin
    is measured per page. Full-width lines only — indented first lines and
    short centred ones would drag a mean, and are a minority either way.
    """
    by_page: dict[int, list[int]] = {}
    for ln in lines:
        if len(ln.text) >= 30:
            by_page.setdefault(ln.page, []).append(ln.x0)
    return {p: int(median(xs)) for p, xs in by_page.items()}


def is_folio(text: str) -> bool:
    return bool(_FOLIO.match(text.strip()))


def caps_core(text: str) -> str:
    """Letters and spaces only, upper-cased — for comparing headings despite
    OCR noise and small-capital misreads ("Tue WorsuIP oF Gop")."""
    return _WS.sub(" ", re.sub(r"[^A-Za-z ]", " ", text)).strip().upper()


def hyphenated_forms(lines: list[Line]) -> set[str]:
    """Hyphenated compounds the book prints INSIDE a line ("to-day").

    When a word breaks at a line end, the hyphen may be the compound's own or
    the compositor's. The book itself is the best witness: a compound it sets
    elsewhere with a hyphen mid-line keeps it; anything else is rejoined.
    """
    forms: set[str] = set()
    for ln in lines:
        for m in re.finditer(r"\b([A-Za-z]+-[A-Za-z]+)\b", ln.text.rstrip("-")):
            forms.add(m.group(1).lower())
    return forms


def join_lines(
    lines: list[Line],
    margin: dict[int, int],
    keep: set[str],
    *,
    indent: int = 30,
) -> list[str]:
    """Body lines → paragraph strings.

    A line indented past the page margin opens a paragraph (so does a centred
    line — a signature, a date); every other line continues the current one,
    whatever page it is on. A word broken at a line end is rejoined unless the
    book prints that compound with its hyphen elsewhere (`keep`), and a dash
    that ends or starts a line closes up to its neighbour.
    """
    paras: list[str] = []
    buf = ""
    for ln in lines:
        text = ln.text
        if ln.x0 - margin.get(ln.page, ln.x0) > indent and buf:
            paras.append(buf)
            buf = ""
        broken = re.search(r"([A-Za-z]+)-$", buf)
        if broken and text[:1].isalpha():
            tail = re.match(r"[A-Za-z]+", text).group(0)
            if f"{broken.group(1)}-{tail}".lower() in keep or tail[:1].isupper():
                buf += text
            else:
                buf = buf[:-1] + text
        elif buf.endswith("—") or text.startswith("—"):
            # A dash at a line's end or start is closed up, as the print sets it.
            buf += text
        else:
            buf = f"{buf} {text}" if buf else text
    if buf:
        paras.append(buf)
    return [_WS.sub(" ", p).strip() for p in paras]
