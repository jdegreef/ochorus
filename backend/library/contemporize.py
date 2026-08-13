"""Contemporize an English Book: produce a "Modern English" edition (content
language ``en-modern``) that keeps the author's voice but reads easily today.

Design (see also .claude/skills/contemporize-book/SKILL.md):

- A modern edition is a SEPARATE ``Book`` row sharing the work's slug, keyed as
  a distinct content language ``en-modern``. The original English row is never
  touched, so a reader can always fall back to the authentic text. This reuses
  the exact ``(slug, language)`` shape the translation pipeline already uses.
- Two passes share one review workflow (``source_type`` ai_unreviewed →
  ai_reviewed via ``manage.py approve_translation``):

    * LIGHT — deterministic, no model, no API key. A high-precision map of
      archaic pronouns, verb forms and obsolete spellings. Precision over
      recall: anything not explicitly listed is left exactly as written, so the
      light edition never guesses and never shifts meaning. Ships today.
    * CAREFUL — model-backed (needs ANTHROPIC_API_KEY; run locally like the
      translation pipeline). Modernizes vocabulary and untangles long Victorian
      sentences while preserving meaning, theology, Scripture wording and the
      author's voice. Simply unavailable — not broken — without a key.

- Scripture is never re-worded by the light pass, and the careful pass is told
  to keep quoted Scripture as the author quoted it.
"""

from __future__ import annotations

import re

from .translation import _BODY_RE, _TITLE_RE, MODEL

# Content-language code for a modern-English edition. NOT a UI locale (Paraglide
# still ships only en/es/sw/lg); it discriminates the Book row and is requested
# per-book by the reader's "Modern English" toggle, never by the locale switch.
MODERN_LANGUAGE = "en-modern"


# --- Light deterministic pass -------------------------------------------------
# Curated, high-precision maps. Multi-word phrases run first so that, e.g.,
# "thou art" becomes "you are" rather than "you art". Single words are limited
# to tokens with no modern meaning (so bare "art"/"ye" are deliberately absent —
# they are only handled inside unambiguous phrases). There is intentionally NO
# general "-eth"/"-est" rule: it mangles irregulars (cometh→"coms"), so every
# verb form is listed explicitly and the long tail is left for the careful pass.

_PHRASES: dict[str, str] = {
    "thou art": "you are",
    "thou wast": "you were",
    "thou hast": "you have",
    "thou hadst": "you had",
    "thou dost": "you do",
    "thou didst": "you did",
    "thou shalt": "you shall",
    "thou wilt": "you will",
    "thou wouldst": "you would",
    "thou canst": "you can",
    "thou couldst": "you could",
    "thou shouldst": "you should",
    "thou mayest": "you may",
    "thou mightest": "you might",
    "art thou": "are you",
    "hast thou": "have you",
    "dost thou": "do you",
    "didst thou": "did you",
    "wilt thou": "will you",
    "shalt thou": "shall you",
    "canst thou": "can you",
    "wouldst thou": "would you",
}

_WORDS: dict[str, str] = {
    # Second-person pronouns / determiners.
    "thou": "you",
    "thee": "you",
    "thy": "your",
    "thine": "yours",
    "thyself": "yourself",
    # Unambiguously archaic verb forms (no modern homograph).
    "hast": "have",
    "hath": "has",
    "dost": "do",
    "doth": "does",
    "doeth": "does",
    "didst": "did",
    "wast": "were",
    "wert": "were",
    "shalt": "shall",
    "wilt": "will",
    "wouldst": "would",
    "couldst": "could",
    "shouldst": "should",
    "canst": "can",
    "mayest": "may",
    "mightest": "might",
    "knowest": "know",
    "knoweth": "knows",
    "sayest": "say",
    "saith": "says",
    "seest": "see",
    "seeth": "sees",
    "hearest": "hear",
    "heareth": "hears",
    "comest": "come",
    "cometh": "comes",
    "goest": "go",
    "goeth": "goes",
    "givest": "give",
    "giveth": "gives",
    "lovest": "love",
    "loveth": "loves",
    "livest": "live",
    "liveth": "lives",
    "believest": "believe",
    "believeth": "believes",
    "walketh": "walks",
    "speaketh": "speaks",
    "maketh": "makes",
    "taketh": "takes",
    "calleth": "calls",
    "dwelleth": "dwells",
    "standeth": "stands",
    "sitteth": "sits",
    "findeth": "finds",
    "lieth": "lies",
    "abideth": "abides",
    "keepeth": "keeps",
    "worketh": "works",
    "bringeth": "brings",
    "seeketh": "seeks",
    "followeth": "follows",
    "teacheth": "teaches",
    "leadeth": "leads",
    "trusteth": "trusts",
    "sendeth": "sends",
    "receiveth": "receives",
    "reigneth": "reigns",
    # Obsolete spellings / adverbs with a plain modern equivalent.
    "shew": "show",
    "shews": "shows",
    "shewed": "showed",
    "shewn": "shown",
    "sheweth": "shows",
    "unto": "to",
    "whilst": "while",
    "amongst": "among",
    "betwixt": "between",
    "hearken": "listen",
    "peradventure": "perhaps",
}


def _match_case(source: str, repl: str) -> str:
    """Give ``repl`` the capitalization of ``source`` (first-letter only)."""
    if source[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def _compile(mapping: dict[str, str]) -> tuple[re.Pattern, dict[str, str]]:
    # Longest keys first so multi-word / longer tokens win the alternation.
    keys = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b", re.IGNORECASE
    )
    lut = {k.lower(): v for k, v in mapping.items()}
    return pattern, lut


_PHRASE_RE, _PHRASE_LUT = _compile(_PHRASES)
_WORD_RE, _WORD_LUT = _compile(_WORDS)


def modernize_light(text: str) -> str:
    """Deterministic light modernization of archaic English.

    Safe to run on the sanitized chapter HTML directly: the archaic tokens never
    collide with the tag/attribute vocabulary in use (p, h2, h3, blockquote, em,
    i, hr, class), so only human-readable text is rewritten. Preserves meaning,
    Scripture wording, punctuation and structure.
    """

    def sub_phrase(m: re.Match) -> str:
        return _match_case(m.group(0), _PHRASE_LUT[m.group(0).lower()])

    def sub_word(m: re.Match) -> str:
        return _match_case(m.group(0), _WORD_LUT[m.group(0).lower()])

    text = _PHRASE_RE.sub(sub_phrase, text)
    text = _WORD_RE.sub(sub_word, text)
    return text


# --- Careful model-backed pass ------------------------------------------------
# Reuses the translation pipeline's streaming + wrapper-tag protocol (and the
# same MODEL), so a modern edition is produced exactly like a translation —
# locally, shipped as data, never needing a key in production.


def system_prompt_modern() -> str:
    return """You are a sensitive editor who modernizes classic Christian devotional prose \
(Andrew Murray, Charles Spurgeon, Watchman Nee and their contemporaries) into clear, \
contemporary English for today's readers.

Rules, in priority order:

1. MEANING AND THEOLOGY ARE ABSOLUTE. Never soften, sharpen, or shift the doctrinal meaning \
of a sentence. Where the English is ambiguous, keep the ambiguity rather than resolving it.
2. SCRIPTURE QUOTATIONS STAY AS THE AUTHOR QUOTED THEM. When the chapter quotes or closely \
paraphrases the Bible, preserve that quoted wording; modernize only the author's own prose \
around it.
3. PRESERVE THE AUTHOR'S VOICE — tone, imagery, cadence, rhetorical force. You are modernizing, \
not rewriting from scratch. Keep it recognizably the same author.
4. WHAT TO MODERNIZE: archaic pronouns and verbs (thou/thee/thy, hath/cometh), obsolete or \
now-confusing vocabulary, and sentences so long or convoluted they impede a modern reader — \
which you may split into shorter sentences. Do NOT merge paragraphs, add content, summarize, \
or omit anything.
5. HTML STRUCTURE IS PRESERVED EXACTLY: the body is sanitized HTML. Keep every tag, in order, \
as-is (<p>, <h2>, <h3>, <blockquote>, <em>, <i>, <hr>). Modernize only the human-readable text \
inside them. Never add, remove, or reorder tags.
6. Keep roughly the same length; this is an edited edition, not an abridgement.

You receive a chapter wrapped in <chapter_title> and <chapter_body> tags. Respond with ONLY \
the modernized chapter in the exact same wrapper tags — no preamble, no notes, no commentary."""


def modernize_chapter(
    client, title: str, body_html: str, *, effort: str = "high"
) -> tuple[str, str, object]:
    """Modernize one chapter (or any title+body unit). Returns (title, body, usage)."""
    user = (
        f"<chapter_title>{title}</chapter_title>\n"
        f"<chapter_body>\n{body_html}\n</chapter_body>"
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=system_prompt_modern(),
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()

    text = "".join(b.text for b in message.content if b.type == "text")
    t = _TITLE_RE.search(text)
    b = _BODY_RE.search(text)
    if not t or not b:
        raise ValueError(f"model response missing wrapper tags (got {text[:200]!r}...)")
    return t.group(1), b.group(1).strip(), message.usage
