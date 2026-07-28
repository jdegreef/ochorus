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

# --- Target languages --------------------------------------------------------
# bible: the Take Root translation code whose wording is authoritative for
# Scripture quotations. Every code below is verified against the live API
# (GET /api/bible/<code>/JHN/1/ → 200 with verse text). The code is read ONLY at
# translation time — seeds and tests never hit the API — so a wrong value can't
# break the build, but it WILL garble a content job's scripture. Verify any new
# one before running its first job.
#
# Prefer a PUBLIC-DOMAIN text: this is a public-domain library, and a CC-BY
# Bible would put an attribution obligation on every quotation we render.

LANGUAGES: dict[str, dict] = {
    "es": {
        "name": "Spanish",
        "native": "Español",
        "bible": "rv1858",
        "bible_label": "Reina-Valera (1858/1862)",
        "glossary": {
            "justification": "justificación",
            "sanctification": "santificación",
            "atonement": "expiación",
            "grace": "gracia",
            "the flesh": "la carne",
            "abide": "permanecer",
            "the Holy Spirit": "el Espíritu Santo",
            "the Lord": "el Señor",
            "godliness": "piedad",
            "intercession": "intercesión",
            "surrender": "entrega / rendición",
        },
    },
    "sw": {
        "name": "Swahili",
        "native": "Kiswahili",
        "bible": "swhonen",
        "bible_label": "Swahili Union-tradition (open)",
        "glossary": {
            "justification": "kuhesabiwa haki",
            "sanctification": "utakaso",
            "atonement": "upatanisho",
            "grace": "neema",
            "the flesh": "mwili",
            "abide": "kukaa (ndani ya Kristo)",
            "the Holy Spirit": "Roho Mtakatifu",
            "the Lord": "Bwana",
            "godliness": "utauwa",
            "intercession": "maombezi",
            "surrender": "kujisalimisha",
        },
    },
    "lg": {
        "name": "Luganda",
        "native": "Luganda",
        "bible": "lug",
        "bible_label": "Luganda Bible (open)",
        "glossary": {
            "justification": "okuweebwa obutuukirivu",
            "sanctification": "okutukuzibwa",
            "atonement": "okutangirira",
            "grace": "ekisa",
            "the flesh": "omubiri",
            "abide": "okubeera (mu Kristo)",
            "the Holy Spirit": "Omwoyo Omutukuvu",
            "the Lord": "Mukama",
            "godliness": "okutya Katonda",
            "intercession": "okwegayiririra abalala",
            "surrender": "okwewaayo",
        },
    },
    "pt": {
        "name": "Portuguese",
        "native": "Português",
        # "almeida" was a guess and 404s. There is no standalone Almeida on Take
        # Root; both Portuguese options are Bíblia Livre editions descended from
        # it. Chose the PUBLIC-DOMAIN one — the alternative, porbr2018 ("Bíblia
        # Livre", CC BY 4.0, © 2018 Diego Santos, Mario Sérgio & Marco Teles),
        # would require carrying that attribution wherever we quote scripture.
        # porbrbsl also keeps the Almeida-tradition wording ("No princípio era o
        # Verbo" vs porbr2018's "a Palavra").
        "bible": "porbrbsl",
        "bible_label": "Bíblia Livre para o Mundo (public domain)",
        "glossary": {
            "justification": "justificação",
            "sanctification": "santificação",
            "atonement": "expiação",
            "grace": "graça",
            "the flesh": "a carne",
            "abide": "permanecer",
            "the Holy Spirit": "o Espírito Santo",
            "the Lord": "o Senhor",
            "godliness": "piedade",
            "intercession": "intercessão",
            "surrender": "entrega / rendição",
        },
    },
}

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
    cfg = LANGUAGES[language]
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
    cfg = LANGUAGES[language]
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


def translate_book_meta(
    client, language: str, title: str, subtitle: str, description: str
) -> dict:
    """Translate the book's title/subtitle/description (single structured call)."""
    cfg = LANGUAGES[language]
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
    cfg = LANGUAGES[language]
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
