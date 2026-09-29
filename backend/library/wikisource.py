"""Read a transcribed Wikisource page as clean reading blocks.

Wikisource transcriptions are proofread against a scan (``Page:`` namespace)
and served through the MediaWiki ``action=parse`` API as HTML. That HTML is
furniture-heavy: a header template, a page-number anchor every page, footnote
markers and a reference list, drop initials split from their word, small caps,
and — for some layouts — paragraphs set inside tables. This module strips all
of it and returns the page as an ordered list of ``Block``s, leaving the
editorial decisions (which centred lines are headings, what to drop) to the
build command that knows the book.

Used by the Pascal build commands; nothing here is Pascal-specific.
"""

from __future__ import annotations

import re
from typing import NamedTuple

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

USER_AGENT = "OchorusBot/1.0 (https://ochorus.com)"

# Furniture removed before any text is read.
_DROP = (
    "style, link, pre, sup.reference, span.pagenum, div.reflist, ol.references, "
    "div.wst-nop, .ws-noexport, .mw-editsection"
)
_ZERO_WIDTH = re.compile("[​‌‍﻿]")


class Block(NamedTuple):
    #: "p" — a paragraph; "heading" — an <h2>–<h6>; "center" — a centred line
    #: (a heading, a numeral, an ornament: the caller decides); "right" — a
    #: right-set line (a dateline, a signature).
    kind: str
    #: Inline HTML: text with <em>/<strong> only.
    html: str

    @property
    def text(self) -> str:
        return re.sub(r"<[^>]+>", "", self.html)


def fetch(host: str, title: str) -> str:
    """The rendered HTML of ``title`` on ``host`` (e.g. ``en.wikisource.org``)."""
    resp = requests.get(
        f"https://{host}/w/api.php",
        params={"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "parse" not in data:
        raise ValueError(f"{host}: no page {title!r}: {data.get('error', {}).get('info', data)}")
    return data["parse"]["text"]["*"]


def _join_drop_initial(soup: BeautifulSoup) -> None:
    """``<span class=dropinitial>W</span>E have`` → ``We have``.

    The printed word is set in capitals after its initial ("WE", "HERE"), so
    the capital run that follows the initial is lowered to rejoin the word.
    """
    for cap in soup.select("span.dropinitial"):
        letter = cap.get_text(strip=True)
        nxt = cap.next_sibling
        if isinstance(nxt, NavigableString):
            m = re.match(r"([A-Z]*)(.*)", str(nxt), re.S)
            nxt.replace_with(letter + m.group(1).lower() + m.group(2))
            cap.decompose()
        else:
            cap.replace_with(letter)


def _inline(node: Tag) -> str:
    for tag in node.select("i, cite"):
        tag.name = "em"
        tag.attrs = {}
    for tag in node.select("b"):
        tag.name = "strong"
        tag.attrs = {}
    for tag in node.find_all(True):
        if tag.name == "br":
            tag.replace_with(" ")
        elif tag.name not in ("em", "strong"):
            tag.unwrap()
    text = _ZERO_WIDTH.sub("", node.decode_contents())
    text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    return re.sub(r"<(em|strong)>\s*</\1>", "", text)


def section_title(html: str) -> str:
    """The header template's section line ("Letter from Pascal to …"), if any."""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(".header-section-text")
    return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else ""


def blocks(html: str) -> list[Block]:
    """The page's reading text, in order, furniture removed.

    Only the text transcluded from the scan (``div.prp-pages-output``) is read:
    the header template around it is navigation, and on some pages it is left
    unclosed so that the transcluded text sits INSIDE its notes block — which is
    why the header cannot simply be deleted.
    """
    page = BeautifulSoup(html, "html.parser")
    # Lift the transcluded text out FIRST: the header wrapper carries
    # `ws-noexport`, so cleaning before lifting would delete the letter with it.
    roots = page.select("div.prp-pages-output")
    soup = BeautifulSoup("".join(str(r) for r in roots) if roots else html, "html.parser")
    for el in soup.select(_DROP):
        el.decompose()
    _join_drop_initial(soup)

    out: list[Block] = []
    for el in soup.find_all(["p", "table", "div", "h2", "h3", "h4", "h5", "h6"]):
        if el.find_parent(["p", "table"]):
            continue
        classes = set(el.get("class") or [])
        if el.name[0] == "h" and el.name != "hr":
            html_ = _inline(el)
            if html_:
                out.append(Block("heading", html_))
            continue
        if el.name == "table":
            # A paragraph set in a table with dotted leaders: the text is the
            # first cell of each row; the rest are the leaders.
            for cell in el.select("td.dotted"):
                html_ = _inline(cell)
                if html_:
                    out.append(Block("p", html_))
            continue
        if el.name == "div":
            # A centred block nested in another is read with its parent.
            if el.find_parent("div", class_=["wst-center", "wst-right"]):
                continue
            if classes & {"wst-center", "wst-right"}:
                kind = "center" if "wst-center" in classes else "right"
                for line in el.find_all("p") or [el]:
                    html_ = _inline(line)
                    if html_:
                        out.append(Block(kind, html_))
            continue
        if el.find_parent("div", class_=["wst-center", "wst-right"]):
            continue
        html_ = _inline(el)
        if html_:
            out.append(Block("p", html_))
    return out
