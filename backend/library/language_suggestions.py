"""Which language to add next — ranked, with everything the form needs.

Adding a language used to mean typing a code, two names, a Take Root Bible code
and an RTL flag from memory, then hunting the catalogue for whether a decent
Bible even exists. The Bible is the part that matters most and is hardest to
guess: scripture is quoted verbatim from it, so a language Take Root has no
text for cannot be translated at all.

So a language is only suggested if Take Root can supply its scripture, and the
list is then ordered by REACH — the languages the library could serve the most
people in. Each row carries its Bible's licence as a fact, not a gate.

Two inputs, deliberately separated:

* **Live, from Take Root** (``/api/bible/translations/``) — the Bible code,
  label, licence and script direction. Authoritative and self-updating: when
  Take Root loads a new Bible, the suggestion appears here with no code change.
* **Editorial, in this file** — native name and approximate global reach. Native
  names aren't in the catalogue, and reach is a judgement call. Both are stated
  plainly below rather than dressed up as data.

Reach is L1+L2 speakers in millions, rounded, from the usual public estimates.
It orders a list; it is not a statistic anyone should quote.
"""

from __future__ import annotations

import requests

TAKEROOT_API = "https://api.takeroot.bible"

# Ancient and liturgical languages are in the Bible catalogue as SOURCE texts
# (Tischendorf, the Aleppo Codex, the Vulgate, the Peshitta). Nobody reads a
# devotional library in them, so they are never suggested as a UI language.
NOT_A_READING_LANGUAGE = {"grc", "hbo", "syr", "la", "eo"}

# Display names that the Take Root catalogue gets wrong or leaves ambiguous. It
# is the authority on Bibles, not on language naming, and it is a different
# app — so these are corrected here rather than propagated to admins.
NAME_OVERRIDES = {
    "zh-hans": "Chinese (Simplified)",   # catalogue calls both scripts "Chinese"
    "zh-hant": "Chinese (Traditional)",
    "my": "Burmese",                     # catalogue: "Myanmar Burmse" (sic)
    "nb": "Norwegian Bokmål",            # catalogue: "Norwegian bokmal"
    "el": "Greek",                       # catalogue: "Greek Modern"
}

# code -> (native name, approximate global speakers in millions)
LANGUAGE_REFERENCE: dict[str, tuple[str, int]] = {
    "zh-hans": ("简体中文", 1100),
    "zh-hant": ("繁體中文", 1100),
    "hi": ("हिन्दी", 600),
    "es": ("Español", 560),
    "ar": ("العربية", 400),
    "fr": ("Français", 310),
    "bn": ("বাংলা", 270),
    "pt": ("Português", 260),
    "ru": ("Русский", 255),
    "sw": ("Kiswahili", 200),
    "de": ("Deutsch", 135),
    "ja": ("日本語", 125),
    "pa": ("ਪੰਜਾਬੀ", 113),
    "mr": ("मराठी", 95),
    "vi": ("Tiếng Việt", 85),
    "tl": ("Tagalog", 85),
    "ko": ("한국어", 82),
    "it": ("Italiano", 68),
    "gu": ("ગુજરાતી", 62),
    "am": ("አማርኛ", 57),
    "yo": ("Yorùbá", 46),
    "pl": ("Polski", 45),
    "my": ("မြန်မာဘာသာ", 43),
    "uk": ("Українська", 40),
    "ln": ("Lingála", 40),
    "ml": ("മലയാളം", 38),
    "om": ("Afaan Oromoo", 37),
    "nl": ("Nederlands", 25),
    "mg": ("Malagasy", 25),
    "lg": ("Luganda", 20),
    "tw": ("Twi", 20),
    "sn": ("chiShona", 15),
    "ny": ("Chichewa", 14),
    "el": ("Ελληνικά", 13),
    "hu": ("Magyar", 13),
    "sv": ("Svenska", 13),
    "sr": ("Српски", 12),
    "cs": ("Čeština", 11),
    "sq": ("Shqip", 8),
    "hy": ("Հայերեն", 7),
    "hr": ("Hrvatski", 6),
    "da": ("Dansk", 6),
    "fi": ("Suomi", 6),
    "nb": ("Norsk bokmål", 5),
}


def _translations(timeout: int = 20) -> list[dict]:
    """Take Root's Bible catalogue; empty on any failure (suggestions degrade
    to nothing rather than taking the admin page down with them)."""
    try:
        r = requests.get(f"{TAKEROOT_API}/api/bible/translations/", timeout=timeout)
        return r.json() if r.ok else []
    except (requests.RequestException, ValueError):
        return []


def licence_for(bible_code: str, timeout: int = 20) -> tuple[str, bool]:
    """``(licence, known)`` for a Take Root Bible code, straight from the catalogue.

    The admin's Bible box is free text — the picker fills it in, but a code can
    also be typed, and typing ``irvhin`` by hand is not a hypothetical: it is the
    placeholder in that very field. So the licence must be looked up from the
    code that was actually submitted rather than taken from whatever the form
    remembered, or the attribution gate is one keystroke wide.

    ``known`` is False when the catalogue could not be reached or does not list
    the code. Callers must not read that as "public domain" — it is "we could not
    ask", and it is the one case where the client's own answer is worth keeping.
    """
    for t in _translations(timeout=timeout):
        if t.get("code") != bible_code:
            continue
        if t.get("is_public_domain"):
            return "", True
        # A licensed row with a blank `license` string still owes attribution;
        # saying so in words beats recording nothing and skipping the check.
        return t.get("license", "").strip() or "licensed (terms unstated)", True
    return "", False


def suggestions(existing: set[str] | None = None, limit: int = 30) -> list[dict]:
    """Languages worth adding next, best Bible first, then by reach.

    A language only appears if Take Root can actually supply its scripture —
    suggesting one we cannot quote would be suggesting a broken translation job.
    """
    existing = existing or set()
    best: dict[str, dict] = {}
    for t in _translations():
        code = t.get("language_code")
        if code in NOT_A_READING_LANGUAGE or code in existing:
            continue
        if code not in LANGUAGE_REFERENCE:
            continue
        current = best.get(code)
        # Prefer a public-domain text; among equals, keep the first listed.
        if current is None or (t.get("is_public_domain") and not current["public_domain"]):
            native, speakers = LANGUAGE_REFERENCE[code]
            best[code] = {
                "code": code,
                "name": NAME_OVERRIDES.get(code) or t.get("language_name", "").strip(),
                "native_name": native,
                "rtl": t.get("direction") == "rtl",
                "bible": t.get("code"),
                "bible_label": t.get("name", "").strip(),
                "public_domain": bool(t.get("is_public_domain")),
                "licence": t.get("license", ""),
                "attribution_required": not bool(t.get("is_public_domain")),
                "speakers_millions": speakers,
            }
    # Ordered by REACH. An earlier cut sorted public-domain first and pushed
    # Hindi — 600M speakers — to 28th, below Norwegian. Reach is the point:
    # these are the languages the library could serve most people in. The
    # licence rides along as a fact about each row (a CC-BY Bible wants an
    # attribution line somewhere) but it does not decide the order, and public
    # domain only breaks ties between equally-spoken languages.
    ranked = sorted(
        best.values(),
        key=lambda s: (-s["speakers_millions"], not s["public_domain"], s["code"]),
    )
    return ranked[:limit]
