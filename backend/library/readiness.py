"""Is a language ready to go live? — computed, not remembered.

One place that answers the question, so the admin report, the go-live action and
anyone asking on the command line all agree. Every check is derived from data;
nothing here is a stored verdict that could drift from reality.

**No review gate.** Translations go live wearing their "awaiting native review"
badge, so review state is deliberately not a check — that was an explicit
product decision, not an oversight.

**Thresholds are per-language** and admin-editable (``Language.min_books`` and
friends). A language with a big catalogue behind it should clear a higher bar
than a first beachhead language, and 0 disables a check.

**Why a check can be UNKNOWN.** Two checks can't always be answered where they
are asked:

- *Bible* needs a live call to the Take Root API. If the network is unavailable
  we report ``unknown`` rather than ``fail`` — "we couldn't ask" is not "the
  Bible is wrong", and failing closed here would block a launch for a reason
  that has nothing to do with the language.
- *Interface strings* live in ``frontend/messages/*.json``, and the API
  container is built from ``backend/`` alone — it genuinely cannot see them. Read
  when present (a dev checkout), ``unknown`` otherwise.

``unknown`` does **not** block readiness, and that is safe rather than lax: the
interface-completeness rule is enforced at *build* time by
``messageCatalogues.test.ts``, which fails the build for any advertised locale
with a missing key. So a language marked live with an incomplete catalogue fails
its deploy loudly instead of shipping English strings quietly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from django.conf import settings

from .models import (
    Author,
    AuthorTranslation,
    Book,
    Language,
    Plan,
    Sermon,
    Topic,
    TopicTranslation,
)
from .translation import GLOSSARY_TERMS, missing_glossary_terms

PASS = "pass"
FAIL = "fail"
UNKNOWN = "unknown"
SKIPPED = "skipped"  # threshold set to 0, or not applicable to this language


@dataclass
class Check:
    key: str
    label: str
    status: str
    detail: str
    current: int | None = None
    required: int | None = None

    @property
    def blocking(self) -> bool:
        return self.status == FAIL


@dataclass
class Report:
    code: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """No check is failing. ``unknown`` doesn't block — see the module docstring."""
        return not any(c.blocking for c in self.checks)

    @property
    def blockers(self) -> list[Check]:
        return [c for c in self.checks if c.blocking]

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "ready": self.ready,
            "blocking": [c.key for c in self.blockers],
            "checks": [asdict(c) for c in self.checks],
        }


# --- individual checks --------------------------------------------------------


def _count_check(key: str, label: str, current: int, required: int, noun: str) -> Check:
    if required <= 0:
        return Check(
            key,
            label,
            SKIPPED,
            f"No minimum set — {current} {noun} present.",
            current,
            required,
        )
    ok = current >= required
    return Check(
        key,
        label,
        PASS if ok else FAIL,
        (
            f"{current} of {required} {noun}."
            if ok
            else f"{current} {noun} — needs {required}."
        ),
        current,
        required,
    )


def _bible_check(lang: Language) -> Check:
    if lang.is_source:
        return Check(
            "bible", "Bible", SKIPPED, "English is the source language.", None, None
        )
    if not lang.bible_code:
        return Check(
            "bible",
            "Bible",
            FAIL,
            "No Bible configured — scripture would be omitted from translations.",
        )
    # Imported lazily: this is the only check that touches the network, and the
    # module is imported by admin views that mostly don't need it.
    from .translation import verify_bible_code

    try:
        verify_bible_code(lang.code)
    except ValueError as e:
        # `fetch_chapter` swallows request errors and returns None, so
        # verify_bible_code raises the same ValueError for "wrong code" as for
        # "the API was unreachable". Those must not be reported the same way: a
        # network outage would otherwise read as a broken Bible and block a
        # launch for a reason that has nothing to do with the language. Probe
        # reachability to tell them apart.
        if not api_reachable():
            return Check(
                "bible",
                "Bible",
                UNKNOWN,
                (
                    f"Could not reach the Bible API to verify {lang.bible_code}. "
                    "Re-run this check from somewhere with access."
                ),
            )
        return Check("bible", "Bible", FAIL, str(e))
    return Check("bible", "Bible", PASS, f"{lang.bible_label or lang.bible_code} resolves.")


def api_reachable() -> bool:
    """Whether the Take Root API answered at all — not whether a code is valid."""
    import requests

    from .translation import TAKEROOT_API

    try:
        requests.get(TAKEROOT_API, timeout=5)
        return True
    except requests.RequestException:
        return False


def _glossary_check(lang: Language) -> Check:
    if lang.is_source:
        return Check(
            "glossary", "Glossary", SKIPPED, "English is the source language.", None, None
        )
    missing = missing_glossary_terms(lang.glossary)
    have = len(GLOSSARY_TERMS) - len(missing)
    if missing:
        return Check(
            "glossary",
            "Glossary",
            FAIL,
            f"{len(missing)} term(s) missing: {', '.join(missing)}.",
            have,
            len(GLOSSARY_TERMS),
        )
    return Check(
        "glossary",
        "Glossary",
        PASS,
        f"All {len(GLOSSARY_TERMS)} theological terms defined.",
        have,
        len(GLOSSARY_TERMS),
    )


def _bios_present(code: str, is_source: bool) -> int:
    if is_source:
        return Author.objects.exclude(bio="").exclude(is_imprint=True).count()
    # A bio counts if either the short or the long form exists in this language —
    # they are translated in separate passes.
    return (
        AuthorTranslation.objects.filter(language=code)
        .exclude(bio="", bio_html="")
        .values("author_id")
        .distinct()
        .count()
    )


def _topics_check(lang: Language) -> Check:
    total = Topic.objects.filter(is_published=True).count()
    if not lang.require_all_topics:
        return Check("topics", "Topic shelves", SKIPPED, "Not required for this language.")
    if lang.is_source:
        return Check(
            "topics", "Topic shelves", PASS, f"All {total} shelves are English originals."
        )
    have = (
        TopicTranslation.objects.filter(language=lang.code)
        .exclude(title="")
        .values("topic_id")
        .distinct()
        .count()
    )
    if have >= total:
        return Check("topics", "Topic shelves", PASS, f"All {total} translated.", have, total)
    return Check(
        "topics",
        "Topic shelves",
        FAIL,
        (
            f"{have} of {total} translated — an untranslated shelf is hidden in this "
            "language, so the topics page would be short."
        ),
        have,
        total,
    )


def _messages_dir() -> Path | None:
    """The frontend's message catalogues, when this process can see them."""
    root = Path(settings.BASE_DIR).parent / "frontend" / "messages"
    return root if root.is_dir() else None


def _ui_check(lang: Language) -> Check:
    if lang.is_source:
        return Check("ui", "Interface strings", SKIPPED, "English is the source.")
    if not lang.require_complete_ui:
        return Check("ui", "Interface strings", SKIPPED, "Not required for this language.")
    msgs = _messages_dir()
    if msgs is None:
        return Check(
            "ui",
            "Interface strings",
            UNKNOWN,
            (
                "The API cannot see the frontend catalogues from here. Enforced at "
                "build time instead: a live locale with a missing key fails the build."
            ),
        )
    try:
        base = {k for k in json.loads((msgs / "en.json").read_text("utf-8")) if k[:1] != "$"}
        target_file = msgs / f"{lang.code}.json"
        if not target_file.exists():
            return Check(
                "ui", "Interface strings", FAIL, f"No {lang.code}.json catalogue.", 0, len(base)
            )
        have = {k for k in json.loads(target_file.read_text("utf-8")) if k[:1] != "$"}
    except (OSError, ValueError) as e:
        return Check("ui", "Interface strings", UNKNOWN, f"Could not read catalogues ({e}).")
    missing = len(base - have)
    if missing:
        return Check(
            "ui",
            "Interface strings",
            FAIL,
            f"{missing} string(s) would render in English.",
            len(base) - missing,
            len(base),
        )
    return Check(
        "ui", "Interface strings", PASS, f"All {len(base)} translated.", len(base), len(base)
    )


# --- the report ---------------------------------------------------------------


def report(lang: Language) -> Report:
    """Every readiness check for one language."""
    code = lang.code
    checks = [
        _bible_check(lang),
        _glossary_check(lang),
        _ui_check(lang),
        _count_check(
            "books",
            "Books",
            Book.objects.filter(language=code, is_published=True).count(),
            lang.min_books,
            "books",
        ),
        _count_check(
            "sermons",
            "Sermons",
            Sermon.objects.filter(language=code, is_published=True).count(),
            lang.min_sermons,
            "sermons",
        ),
        _count_check(
            "bios",
            "Biographies",
            _bios_present(code, lang.is_source),
            lang.min_bios,
            "biographies",
        ),
        _count_check(
            "plans",
            "Reading plans",
            Plan.objects.filter(language=code, is_published=True).count(),
            lang.min_plans,
            "plans",
        ),
        _topics_check(lang),
    ]
    return Report(code=code, checks=checks)
