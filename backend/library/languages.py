"""Reading the Language registry — one cached accessor, one home.

Language rows are read on nearly every serialized response (a book's language
label, an admin list, the analytics breakdown) but change only when an admin
edits one. So they are cached in-process and invalidated by a signal rather than
queried per call: ``_language_entry`` used to be a dict lookup against a
hardcoded map, and several callers loop over content rows, so a naive query per
call would have turned a page render into an N+1.

**Staleness, deliberately bounded.** The cache is per-process, so after an admin
edit each worker refreshes on its own next miss — for display names that is
invisible. Anything that *acts* on ``status`` (the go-live path) must read the
row directly instead of trusting this cache: a launch is a decision, not a
label, and it also triggers a deploy which restarts every worker anyway.
"""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Language

_cache: dict[str, dict] | None = None


def _build() -> dict[str, dict]:
    return {
        lang.code: {
            "code": lang.code,
            "name": lang.name,
            "native_name": lang.native_name,
            "rtl": lang.rtl,
            "is_source": lang.is_source,
            "status": lang.status,
        }
        for lang in Language.objects.all()
    }


def language_map() -> dict[str, dict]:
    """Every known language, keyed by code. Cached; see the module docstring."""
    global _cache
    if _cache is None:
        _cache = _build()
    return _cache


def invalidate() -> None:
    """Drop the cache — called by the signals below, and by tests."""
    global _cache
    _cache = None


def entry(code: str) -> dict:
    """The display entry for ``code``.

    Falls back to the bare code for a language with no row, so an unexpected
    value in old content still renders something rather than raising. Shape is
    the public one (code/name/native_name) plus the registry's own flags.
    """
    known = language_map().get(code)
    if known:
        return dict(known)
    return {
        "code": code,
        "name": code,
        "native_name": code,
        "rtl": False,
        "is_source": False,
        "status": Language.Status.DRAFT,
    }


def known_codes() -> set[str]:
    """Codes the registry knows — the allowlist for "is this a real language?".

    Straight from the DB, not the display cache. The cache is per-process, so a
    language just added from the admin would be missing from *other* workers'
    copies until they happened to miss — and this is a gate, not a label: the
    first thing you do after adding a language is queue work for it, and being
    told it doesn't exist would be baffling.
    """
    return set(Language.objects.values_list("code", flat=True))


def target_codes() -> list[str]:
    """Codes a translation job can target — every known language but the source."""
    return sorted(
        Language.objects.filter(is_source=False).values_list("code", flat=True)
    )


def config(code: str) -> dict:
    """Everything the translator needs to work in ``code``, from the registry.

    Read straight from the row, not from the display cache: a translation job is
    a long, paid operation started by hand, so one query is free, and using
    stale glossary terms would be expensive to discover.

    Raises ``ValueError`` for an unknown language or the source language — both
    mean the caller asked for something that cannot be a translation target.
    """
    lang = Language.objects.filter(code=code).first()
    if lang is None:
        known = ", ".join(target_codes())
        raise ValueError(
            f"Unknown language {code!r}. Known translation targets: {known}. "
            "Add a language from the admin (Dashboard → Languages) first."
        )
    if lang.is_source:
        raise ValueError(f"{code!r} is the source language — it is not a translation target.")
    return {
        "code": lang.code,
        "name": lang.name,
        "native": lang.native_name,
        "bible": lang.bible_code,
        "bible_label": lang.bible_label,
        "glossary": dict(lang.glossary or {}),
    }


def live_codes() -> list[str]:
    """Codes readers are offered, in display order.

    This is what the build asks for when deciding which locales to prerender and
    advertise. Read from the DB rather than the cache: it decides what ships.
    """
    return list(
        Language.objects.filter(status=Language.Status.LIVE)
        .order_by("sort_order", "name")
        .values_list("code", flat=True)
    )


@receiver(post_save, sender=Language)
@receiver(post_delete, sender=Language)
def _invalidate_on_change(**_kwargs) -> None:
    invalidate()
