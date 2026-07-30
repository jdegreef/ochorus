"""AI-translate-then-review pipeline: translate a Book's chapters into a target
language with Claude, substituting Scripture quotations from a trusted Bible.

Design decisions (see also .claude/skills/translate-book/SKILL.md):

- Translations are produced LOCALLY (management command) and shipped as data,
  so prod never needs an Anthropic key.
- Scripture quotations are never left to the model's memory: Bible references
  in the chapter are detected, the verses fetched in the target language from
  the Take Root Bible API (api.takeroot.bible — public-domain / openly licensed
  translations), and supplied to the model as the authoritative wording.
- Every translated Book row is created with source_type="ai_unreviewed"; the
  reader shows a badge until a native reviewer approves it
  (``manage.py approve_translation``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import requests

from .languages import config as language_config

# A target language's config — its Bible and its glossary — is read from the
# Language REGISTRY (``language_config``), not from a dict in this file. That is
# what makes "Add a language" in the admin produce a language you can actually
# translate into: the row an admin creates is the same row these functions read.
# ``library/language_seed.py`` holds the repo-owned rows the seed re-asserts.

# Every language's glossary must cover exactly these terms — the shared
# discipline that keeps theological vocabulary consistent across translations.
# Pinned by a test, so a new language can't ship a partial glossary.
GLOSSARY_TERMS = (
    "justification",
    "sanctification",
    "atonement",
    "grace",
    "the flesh",
    "abide",
    "the Holy Spirit",
    "the Lord",
    "godliness",
    "intercession",
    "surrender",
)

# --- Bible reference detection ------------------------------------------------
# English book name (as it appears in the source books) -> USFM code.

BOOK_USFM: dict[str, str] = {
    "genesis": "GEN", "exodus": "EXO", "leviticus": "LEV", "numbers": "NUM",
    "deuteronomy": "DEU", "joshua": "JOS", "judges": "JDG", "ruth": "RUT",
    "1 samuel": "1SA", "2 samuel": "2SA", "1 kings": "1KI", "2 kings": "2KI",
    "1 chronicles": "1CH", "2 chronicles": "2CH", "ezra": "EZR",
    "nehemiah": "NEH", "esther": "EST", "job": "JOB",
    "psalm": "PSA", "psalms": "PSA", "proverbs": "PRO",
    "ecclesiastes": "ECC", "song of solomon": "SNG", "song of songs": "SNG",
    "isaiah": "ISA", "jeremiah": "JER", "lamentations": "LAM",
    "ezekiel": "EZK", "daniel": "DAN", "hosea": "HOS", "joel": "JOL",
    "amos": "AMO", "obadiah": "OBA", "jonah": "JON", "micah": "MIC",
    "nahum": "NAM", "habakkuk": "HAB", "zephaniah": "ZEP", "haggai": "HAG",
    "zechariah": "ZEC", "malachi": "MAL",
    "matthew": "MAT", "mark": "MRK", "luke": "LUK", "john": "JHN",
    "acts": "ACT", "romans": "ROM",
    "1 corinthians": "1CO", "2 corinthians": "2CO", "galatians": "GAL",
    "ephesians": "EPH", "philippians": "PHP", "colossians": "COL",
    "1 thessalonians": "1TH", "2 thessalonians": "2TH",
    "1 timothy": "1TI", "2 timothy": "2TI", "titus": "TIT",
    "philemon": "PHM", "hebrews": "HEB", "james": "JAS",
    "1 peter": "1PE", "2 peter": "2PE",
    "1 john": "1JN", "2 john": "2JN", "3 john": "3JN",
    "jude": "JUD", "revelation": "REV",
}

_BOOK_ALT = sorted(BOOK_USFM, key=len, reverse=True)
_REF_RE = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in _BOOK_ALT) + r")\s+(\d{1,3})\s*[:.]\s*(\d{1,3})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Ref:
    usfm: str
    chapter: int


def find_references(text: str) -> list[Ref]:
    """Distinct (book, chapter) references mentioned in the text, in order."""
    seen: list[Ref] = []
    for m in _REF_RE.finditer(text):
        ref = Ref(BOOK_USFM[m.group(1).lower()], int(m.group(2)))
        if ref not in seen:
            seen.append(ref)
    return seen


# --- Scripture fetch (Take Root Bible API) ------------------------------------

TAKEROOT_API = "https://api.takeroot.bible"
_verse_cache: dict[tuple[str, str, int], dict | None] = {}


def fetch_chapter(bible: str, ref: Ref) -> dict | None:
    """Fetch one Bible chapter in the target language; None on any failure."""
    key = (bible, ref.usfm, ref.chapter)
    if key not in _verse_cache:
        try:
            r = requests.get(
                f"{TAKEROOT_API}/api/bible/{bible}/{ref.usfm}/{ref.chapter}/",
                timeout=20,
            )
            _verse_cache[key] = r.json() if r.ok else None
        except requests.RequestException:
            _verse_cache[key] = None
    return _verse_cache[key]


def verify_bible_code(language: str) -> None:
    """Fail fast if a language's configured Bible doesn't resolve.

    scripture_context FAILS OPEN — it skips any passage whose fetch returns
    None — so a wrong code doesn't raise, it silently yields a translation with
    ZERO authoritative scripture, at full model cost, looking entirely normal.
    ("almeida" was such a code, and sat in the tree unnoticed.) Every translate_*
    command calls this before doing paid work; one request, and _verse_cache
    means the job's own JHN 1 lookup reuses it.

    Note the limit: this proves the code RESOLVES, not that it's the right
    language — pt→swhonen would pass. Only review catches that.
    """
    cfg = language_config(language)
    if not (fetch_chapter(cfg["bible"], Ref("JHN", 1)) or {}).get("verses"):
        raise ValueError(
            f"Bible code {cfg['bible']!r} for {language!r} returned no verses from "
            f"{TAKEROOT_API} — scripture would be silently omitted. "
            "Fix the language's Bible code in the admin (or in "
            "library/language_seed.py for a repo-defined language) before "
            "running this job."
        )


def verify_glossary(language: str) -> None:
    """Fail fast if a language's theological glossary is incomplete.

    Same shape of hazard as ``verify_bible_code``: ``system_prompt`` just
    formats whatever terms are present, so a half-filled glossary produces a
    translation that looks fine and renders "justification" however the model
    felt that day — inconsistently, across every chapter, at full cost. Since a
    language can now be created from the admin, the glossary is data, and data
    gets checked before we spend money on it.
    """
    cfg = language_config(language)
    missing = missing_glossary_terms(cfg["glossary"])
    if missing:
        raise ValueError(
            f"Glossary for {language!r} is missing {len(missing)} term(s): "
            f"{', '.join(missing)}. Fill them in on the language's admin page "
            "before running this job."
        )


def missing_glossary_terms(glossary: dict | None) -> list[str]:
    """Terms in ``GLOSSARY_TERMS`` this glossary has no non-empty value for."""
    have = {k for k, v in (glossary or {}).items() if str(v).strip()}
    return [t for t in GLOSSARY_TERMS if t not in have]


def fetch_verse_text(bible: str, ref_text: str) -> str:
    """The single verse a reference points at, in this language's Bible.

    ``scripture_context`` hands a whole chapter to the model as context; a topic
    shelf instead quotes one verse *verbatim*, so it needs the verse itself.

    Returns ``""`` on any failure — an unresolvable reference, a chapter the API
    doesn't have, a verse number outside it. Callers must treat that as absent
    scripture and ship none: verse wording is never the model's to invent (see
    the module docstring), so a blank here must not become a paraphrase.
    """
    m = _REF_RE.search(ref_text or "")
    if not m:
        return ""
    book, chapter, verse = m.group(1).lower(), int(m.group(2)), int(m.group(3))
    data = fetch_chapter(bible, Ref(BOOK_USFM[book], chapter))
    if not data or not data.get("verses"):
        return ""
    for v in data["verses"]:
        if int(v.get("number", 0)) == verse:
            return str(v.get("text", "")).strip()
    return ""


def scripture_context(text: str, bible: str, max_refs: int = 12) -> str:
    """Build the authoritative-scripture prompt block for a chapter."""
    blocks: list[str] = []
    for ref in find_references(text)[:max_refs]:
        data = fetch_chapter(bible, ref)
        if not data or not data.get("verses"):
            continue
        verses = " ".join(f"[{v['number']}] {v['text']}" for v in data["verses"])
        blocks.append(f"<passage reference=\"{data['reference']}\">\n{verses}\n</passage>")
    return "\n\n".join(blocks)


# --- Translation --------------------------------------------------------------

MODEL = "claude-opus-4-8"

_TITLE_RE = re.compile(r"<chapter_title>\s*(.*?)\s*</chapter_title>", re.S)
_BODY_RE = re.compile(r"<chapter_body>\s*(.*?)\s*</chapter_body>", re.S)


def system_prompt(language: str) -> str:
    cfg = language_config(language)
    glossary = "\n".join(f"- {en} → {tr}" for en, tr in cfg["glossary"].items())
    return f"""You are an expert literary translator of classic Christian devotional literature \
(Andrew Murray, Charles Spurgeon, Watchman Nee and their contemporaries) from English into \
{cfg['name']} ({cfg['native']}).

Rules, in priority order:

1. THEOLOGICAL FIDELITY IS ABSOLUTE. Never soften, sharpen, or shift the doctrinal meaning of \
a sentence. Where the English is ambiguous, preserve the ambiguity rather than resolving it.
2. SCRIPTURE QUOTATIONS ARE NOT YOURS TO TRANSLATE. When the chapter quotes or closely \
paraphrases a Bible verse and that passage is supplied to you in <authoritative_scripture>, \
use the supplied {cfg['bible_label']} wording for the quoted words (adjusting only surrounding \
grammar). If a quotation's passage was not supplied, translate it carefully and conservatively.
3. Use this theological glossary consistently:
{glossary}
4. REGISTER: faithful to the author's meaning, but natural, clear, modern {cfg['name']} — the \
prose should read as if written by a devotional author in {cfg['name']}, never word-for-word \
translationese. The source English is often Victorian; translate the meaning, not the syntax.
5. HTML STRUCTURE IS PRESERVED EXACTLY: the body is sanitized HTML. Keep every tag, in order, \
as-is (<p>, <h2>, <h3>, <blockquote>, <em>, <i>, <hr>). Translate only the human-readable text \
inside them. Never add, remove, or reorder tags. Preserve HTML entities where needed.
6. Proper names keep their conventional {cfg['name']} biblical forms where one exists; \
otherwise keep the English form.

You receive a chapter wrapped in <chapter_title> and <chapter_body> tags. Respond with ONLY \
the translated chapter in the exact same wrapper tags — no preamble, no notes, no commentary."""


def translate_chapter(
    client,
    language: str,
    title: str,
    body_html: str,
    *,
    effort: str = "high",
    scripture_source: str | None = None,
) -> tuple[str, str, object]:
    """Translate one chapter (or any title+body unit). Returns (title, body_html, usage).

    ``scripture_source`` overrides the text scanned for Bible references (a
    sermon, say, wants its ``scripture_ref`` included); defaults to the title
    and body.
    """
    cfg = language_config(language)
    scripture = scripture_context(scripture_source or f"{title}\n{body_html}", cfg["bible"])
    user = ""
    if scripture:
        user += f"<authoritative_scripture>\n{scripture}\n</authoritative_scripture>\n\n"
    user += f"<chapter_title>{title}</chapter_title>\n<chapter_body>\n{body_html}\n</chapter_body>"

    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=system_prompt(language),
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()

    text = "".join(b.text for b in message.content if b.type == "text")
    t = _TITLE_RE.search(text)
    b = _BODY_RE.search(text)
    if not t or not b:
        raise ValueError(
            f"model response missing wrapper tags (got {text[:200]!r}...)"
        )
    return t.group(1), b.group(1).strip(), message.usage


BOOK_META_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["title", "subtitle", "description"],
    "additionalProperties": False,
}


# --- Topics -------------------------------------------------------------------
# A topical shelf is a curatorial label: a short title and a 1–2 sentence blurb.
# Its own prose carries no Scripture quotation (the shelf's verse is a separate
# field, fetched from the Bible rather than translated), so this is a plain
# metadata call with no scripture context to assemble.

TOPIC_META_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["title", "description"],
    "additionalProperties": False,
}


def translate_topic_meta(client, language: str, title: str, description: str) -> dict:
    """Translate a topical shelf's title and description (single call)."""
    cfg = language_config(language)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        thinking={"type": "adaptive"},
        system=system_prompt(language),
        output_config={"format": {"type": "json_schema", "schema": TOPIC_META_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Translate this topical shelf's label for a library of classic "
                    "Christian books. The title is a heading a reader scans, so keep "
                    "it short and natural rather than literal; the description is one "
                    "or two sentences of invitation. Return JSON with keys title and "
                    f"description, in {cfg['name']}.\n\n"
                    f"title: {title}\ndescription: {description}"
                ),
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def translate_book_meta(
    client, language: str, title: str, subtitle: str, description: str
) -> dict:
    """Translate the book's title/subtitle/description (single structured call)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        system=system_prompt(language),
        output_config={"format": {"type": "json_schema", "schema": BOOK_META_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Translate this book's metadata. Return JSON with keys title, subtitle, "
                    "description (keep empty strings empty).\n\n"
                    f"title: {title}\nsubtitle: {subtitle}\ndescription: {description}"
                ),
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# --- Sermons ------------------------------------------------------------------
# A sermon is a single title+body unit (no chapters), so it reuses the chapter
# translator — but its scripture_ref (the preached text) is folded into the
# reference scan so that passage is fetched authoritatively too.


def translate_sermon(
    client, language: str, title: str, body_html: str, scripture_ref: str,
    *, effort: str = "high",
) -> tuple[str, str, object]:
    """Translate a sermon's title and body. Returns (title, body_html, usage)."""
    source = f"{scripture_ref}\n{title}\n{body_html}"
    return translate_chapter(
        client, language, title, body_html, effort=effort, scripture_source=source
    )


SCRIPTURE_REF_SCHEMA = {
    "type": "object",
    "properties": {"reference": {"type": "string"}},
    "required": ["reference"],
    "additionalProperties": False,
}


def translate_scripture_ref(client, language: str, ref: str) -> str:
    """Localize a sermon's reference (book name → target language; keep numbers)."""
    if not ref.strip():
        return ""
    cfg = language_config(language)
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        thinking={"type": "adaptive"},
        system=system_prompt(language),
        output_config={"format": {"type": "json_schema", "schema": SCRIPTURE_REF_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Translate this Bible reference's book name into its conventional "
                    f"{cfg['name']} biblical form, keeping the chapter and verse numbers "
                    "exactly as given. Return JSON with a single key 'reference'.\n\n"
                    f"{ref}"
                ),
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["reference"]
