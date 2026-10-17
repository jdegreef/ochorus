"""Turn a reader + content into a rendered email (subject + HTML).

Every email — lifecycle steps, nudges, direct email and admin broadcasts —
renders through ONE template (``emails/blocks.html``) from structured blocks
(emails/blocks.py), never raw HTML, so there is nothing to sanitize. The
fixed-copy emails supply a ``text`` dict (heading, greeting, paragraphs, a CTA,
signoff) that is read as the equivalent blocks. Text direction comes from the
:class:`Language` registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.template.loader import render_to_string

from library.languages import entry as language_entry

from . import blocks as blocks_mod
from . import copy as copy_mod
from . import links, merge_tags

_TEMPLATE = "emails/blocks.html"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str


def _display_name(profile, lang: str) -> str:
    """The reader's first name, or "friend" in the email's language."""
    name = (getattr(profile, "display_name", "") or "").strip()
    if name:
        return name.split()[0]
    return copy_mod.FRIEND.get(copy_mod.base_lang(lang), copy_mod.FRIEND["en"])


def _base_context(subscription, lang: str) -> dict:
    """What every email's frame needs: footer links and text direction."""
    return {
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "preferences_url": links.preferences_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if language_entry(lang).get("rtl") else "ltr",
    }


def _render(text: dict, profile, subscription, lang: str) -> RenderedEmail:
    """Render a fixed-copy email: its ``text`` fields read as blocks. Its CTA
    path is built by code that already chose the edition, so it is used as is."""
    return render_blocks(
        subject=str(text["subject"]),
        content={"preheader": text.get("preheader", ""), "blocks": blocks_mod.legacy_blocks(text)},
        profile=profile,
        subscription=subscription,
        lang=lang,
        localize_buttons=False,
    )


def email_language(profile, subscription) -> str:
    """The language to render in: the reader's email-locale preference when set,
    else their reading locale, else English."""
    override = (getattr(subscription, "email_locale", "") or "").strip()
    return copy_mod.base_lang(override or getattr(profile, "locale", "") or "en")


def _render_step(
    step: str, profile, subscription, lang: str, *, mapping: dict | None = None, cta_path: str | None = None
) -> RenderedEmail:
    """Render an automated email: the admin's published edit in ``lang`` when
    there is one (emails/lifecycle_copy.py), else the code's words. ``mapping``
    fills the step's own placeholders ({next}, {plan}…); ``cta_path`` is where
    a per-reader button goes."""
    from . import lifecycle_copy

    mapping = mapping or {}
    edited = lifecycle_copy.live_email(step, lang)
    if edited is None and lang not in copy_mod.LIFECYCLE[step]:
        # A language with no words of its own gets the English — the edited
        # English when there is one, as it would get the original.
        edited = lifecycle_copy.live_email(step, copy_mod.DEFAULT_LOCALE)
    if edited is not None:
        blocks = [
            {k: _fill(v, mapping) if k in blocks_mod.WORD_FIELDS else v for k, v in b.items()}
            for b in edited["blocks"]
        ]
        return render_blocks(
            subject=_fill(edited["subject"], mapping),
            content={"preheader": _fill(edited["preheader"], mapping), "blocks": blocks},
            profile=profile,
            subscription=subscription,
            lang=lang,
            link=cta_path or "",
            # Like the original: its fixed paths were written for every language.
            localize_buttons=False,
        )
    text = {key: _fill(value, mapping) for key, value in copy_mod.step_copy(step, lang).items()}
    if cta_path is not None:
        text["cta_path"] = cta_path
    return _render(text, profile, subscription, lang)


def render_step(step: str, profile, subscription) -> RenderedEmail:
    """Render lifecycle ``step`` for ``profile`` in their language."""
    return _render_step(step, profile, subscription, email_language(profile, subscription))


def render_welcome(profile, subscription) -> RenderedEmail:
    """Back-compat: render the welcome step."""
    return render_step("welcome", profile, subscription)


def _fill(value, mapping: dict[str, str]):
    """Substitute ``{placeholder}`` tokens in a string or list of strings.

    A literal replace, NOT str.format (same reason as the greeting in _render):
    a stray brace in a book title must never raise mid-send."""
    if isinstance(value, list):
        return [_fill(item, mapping) for item in value]
    if isinstance(value, str):
        for token, replacement in mapping.items():
            value = value.replace(token, replacement)
    return value


def render_series_nudge(
    profile, subscription, *, finished_title: str, next_title: str, cta_path: str
) -> RenderedEmail:
    """Render the finish-the-series nudge for ``profile`` in their language.

    Unlike the static lifecycle steps, this fills the just-finished and next-up
    book titles into the copy and points the CTA at the next volume (``cta_path``
    is resolved per reader by the caller)."""
    lang = email_language(profile, subscription)
    mapping = {"{finished}": finished_title, "{next}": next_title}
    return _render_step("finish_series", profile, subscription, lang, mapping=mapping, cta_path=cta_path)


def render_plan_reminder(
    profile,
    subscription,
    *,
    step: str,
    plan_title: str,
    day: int,
    total: int,
    reading_title: str,
    cta_path: str,
) -> RenderedEmail:
    """Render a reading-plan email (``plan_reminder`` or ``plan_paused``) for
    ``profile``: the plan, the day and today's reading filled into the copy, the
    CTA pointing at that day (``cta_path``, built by the caller)."""
    lang = email_language(profile, subscription)
    mapping = {
        "{plan}": plan_title,
        "{day}": str(day),
        "{total}": str(total),
        "{reading}": reading_title or plan_title,
    }
    return _render_step(step, profile, subscription, lang, mapping=mapping, cta_path=cta_path)


def render_milestone(profile, subscription, *, milestone: int) -> RenderedEmail:
    """Render the reading-milestone card for ``profile``, filling in the count."""
    lang = email_language(profile, subscription)
    return _render_step("milestone", profile, subscription, lang, mapping={"{count}": str(milestone)})


def render_broadcast(
    broadcast, profile, subscription, *, cards=None, any_locale: bool = False
) -> RenderedEmail | None:
    """Render ``broadcast`` for ``profile``, or ``None`` when the campaign has no
    content in the reader's language (nor a usable fallback).

    ``any_locale`` ignores ``strict_locale`` — an admin's test send of a
    campaign written only in a language that isn't their own."""
    lang = email_language(profile, subscription)
    resolved = resolve_broadcast_locale(broadcast, lang, strict=broadcast.strict_locale and not any_locale)
    if resolved is None:
        return None
    return render_blocks(
        subject=str(broadcast.subject.get(resolved, "")),
        content=broadcast.content.get(resolved) or {},
        profile=profile,
        subscription=subscription,
        lang=resolved,
        cards=cards,
    )


def render_blocks(
    *,
    subject: str,
    content: dict,
    profile,
    subscription,
    lang: str,
    cards=None,
    localize_buttons: bool = True,
    values: dict | None = None,
    link: str | None = None,
) -> RenderedEmail:
    """Render one language's block content (emails/blocks.py) for ``profile``.
    Shared by every send and the admin's live preview, so the preview is the
    email. ``cards`` is the caller's library-card cache (``blocks.resolve``),
    which also holds the merge-tag lookups. ``values`` overrides the merge-tag
    values — a preview "as a sample reader". ``link`` is where a button whose
    path is ``{link}`` goes (an automated email's per-reader link)."""
    blocks = blocks_mod.blocks_for(content)
    preheader = content.get("preheader", "")
    if values is None:
        needed = merge_tags.tags_in(
            subject, preheader, *(b.get(f, "") for b in blocks for f in blocks_mod.WORD_FIELDS)
        )
        values = merge_tags.values_for(
            profile, lang, first_name=_display_name(profile, lang), needed=needed, cache=cards
        )
    subject = merge_tags.fill_subject(subject, values, lang)
    context = {
        "subject": subject,
        "preheader": merge_tags.fill_subject(preheader, values, lang),
        "blocks": blocks_mod.resolve(
            blocks,
            lang,
            name=values["first_name"],
            cards=cards,
            localize_buttons=localize_buttons,
            profile=profile,
            values=values,
            link=link,
        ),
        **_base_context(subscription, lang),
    }
    return RenderedEmail(subject=subject, html=render_to_string(_TEMPLATE, context))


def render_direct(text: dict, profile, subscription, lang: str) -> RenderedEmail:
    """Render an admin's one-to-one email through the same safe template.
    ``lang`` is the language the admin wrote it in — it sets the email's
    ``lang``/``dir``, so an English note to an Arabic reader stays left-to-right."""
    return _render(text, profile, subscription, lang)


def sendable_locales(broadcast) -> list[str]:
    """The locales a broadcast can be sent in: it has BOTH a subject and
    content for them."""
    return sorted(set(broadcast.subject) & set(broadcast.content))


def resolve_broadcast_locale(broadcast, lang: str, *, strict: bool | None = None) -> str | None:
    """The locale to actually render: the reader's language, else English, else
    the first locale the broadcast can be sent in — or, for a ``strict_locale``
    campaign (``strict`` overrides it), the reader's language or nothing."""
    locales = sendable_locales(broadcast)
    if broadcast.strict_locale if strict is None else strict:
        return lang if lang in locales else None
    for candidate in (lang, "en"):
        if candidate in locales:
            return candidate
    return locales[0] if locales else None
