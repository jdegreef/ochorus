"""Merge tags: a reader's own details written into an email's words.

An admin writes ``{first_name}`` (or ``{tag|fallback}``) in a subject, heading,
text, button label, image caption or hero banner, and each reader's email fills
it in. The tags are :data:`TAGS`; ``{name}`` is the old spelling of
``{first_name}`` and keeps working.

**A missing value.** A tag can have nothing to say for a reader (no book in
progress, no plan started). Then, in order:

1. the fallback written in the tag — ``{last_book|a classic}`` — is used;
2. else the tag's own default, if it has one (``first_name`` is "friend" in the
   email's language, as it always was);
3. else the **sentence** holding the tag is left out — so "You are on day
   {plan_day} of {plan_name}." simply isn't there for a reader with no plan,
   instead of reading "You are on day  of ." A heading, button label or caption
   with such a tag is left out whole; in a subject the tag is just dropped.

Unknown ``{words}`` are left as they are (the pre-send checks flag them), so a
stray brace in a book title can never break a send. Filling is a literal
replace, never ``str.format``.

Values are looked up per reader, but a batch send looks up a whole batch at
once (:func:`prefetch`) — a tag costs no query per reader.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import copy as copy_mod

#: ``{tag}`` or ``{tag|fallback}``.
TAG = re.compile(r"\{([a-z_]+)(?:\|([^{}\n]*))?\}")
#: A sentence with whatever space follows it, in the scripts the site is
#: written in (Chinese and Japanese stops need no space after them).
_SENTENCE = re.compile(r".*?(?:[.!?…。！？؟।።]+\s*|$)", re.S)


@dataclass(frozen=True)
class Tag:
    key: str
    label: str
    sample: str
    description: str


TAGS: dict[str, Tag] = {
    t.key: t
    for t in (
        Tag("first_name", "First name", "Sarah", "Their first name — “friend” in their language when we don’t know it."),
        Tag("last_book", "Last book", "Absolute Surrender", "The book they read most recently."),
        Tag("plan_name", "Plan name", "Thirty days of prayer", "The reading plan they are following."),
        Tag("plan_day", "Plan day", "12", "The next day of that plan."),
        Tag("books_finished", "Books finished", "5", "How many books they have finished (none ⇒ missing)."),
        Tag("language", "Their language", "English", "The name of the language their email is in."),
    )
}
#: The tags that need a lookup of the reader's reading (the rest are free).
READER_FACT_TAGS = frozenset({"last_book", "plan_name", "plan_day", "books_finished"})
#: Old spellings that still work.
ALIASES = {"name": "first_name"}


def tag_key(raw: str) -> str | None:
    """The tag ``raw`` names, or ``None`` when it isn't a merge tag."""
    raw = ALIASES.get(raw, raw)
    return raw if raw in TAGS else None


def tags_in(*texts: str) -> set[str]:
    """The merge tags used anywhere in ``texts``."""
    return {k for text in texts for m in TAG.finditer(text or "") if (k := tag_key(m.group(1)))}


def tag_names(text: str) -> list[str]:
    """The tag names in ``text``, in order — what a translation must keep (its
    fallbacks may be translated)."""
    return sorted(m.group(1) for m in TAG.finditer(text or ""))


def unknown_in(*texts: str) -> set[str]:
    """``{words}`` in ``texts`` that look like tags but aren't."""
    return {m.group(0) for text in texts for m in TAG.finditer(text or "") if tag_key(m.group(1)) is None}


# --- Values ----------------------------------------------------------------------


def _facts(profile_ids) -> dict[int, dict]:
    """What the tags need to know about each reader, in three queries for any
    number of readers: their latest book, how many they've finished, their
    latest plan."""
    from django.db.models import Count

    from reading.models import PlanProgress, ReadingProgress, WorkKind

    facts: dict[int, dict] = {pk: {} for pk in profile_ids}
    books = (
        ReadingProgress.objects.filter(profile_id__in=profile_ids, kind=WorkKind.BOOK)
        .order_by("profile_id", "-updated_at")
        .values("profile_id", "book_slug", "language")
    )
    for row in books:
        facts[row["profile_id"]].setdefault("book", (row["book_slug"], row["language"]))
    finished = (
        ReadingProgress.objects.filter(profile_id__in=profile_ids, kind=WorkKind.BOOK, finished_at__isnull=False)
        .values("profile_id")
        .annotate(n=Count("id"))
    )
    for row in finished:
        facts[row["profile_id"]]["finished"] = row["n"]
    plans = (
        PlanProgress.objects.filter(profile_id__in=profile_ids)
        .order_by("profile_id", "-updated_at")
        .values("profile_id", "plan_slug", "done")
    )
    for row in plans:
        facts[row["profile_id"]].setdefault("plan", (row["plan_slug"], len(row["done"] or [])))
    return facts


def prefetch(profile_ids, cache: dict) -> None:
    """Look up a batch's facts at once, into a send's cache."""
    for pk, facts in _facts(list(profile_ids)).items():
        cache[("facts", pk)] = facts


def _title(cache: dict, model_name: str, slug: str, lang: str) -> str | None:
    """A published book's or plan's title in ``lang`` (cached per send)."""
    key = ("title", model_name, slug, lang)
    if key not in cache:
        from django.apps import apps

        cache[key] = (
            apps.get_model("library", model_name)
            .objects.filter(slug=slug, language=lang, is_published=True)
            .values_list("title", flat=True)
            .first()
        )
    return cache[key]


def _plan_length(cache: dict, slug: str, lang: str) -> int:
    key = ("plan_days", slug, lang)
    if key not in cache:
        from library.models import PlanDay

        cache[key] = PlanDay.objects.filter(plan__slug=slug, plan__language=lang).count()
    return cache[key]


def values_for(profile, lang: str, *, first_name: str, needed: set[str], cache: dict | None = None) -> dict[str, str | None]:
    """Each ``needed`` tag's value for this reader (``None`` = nothing to say).

    ``first_name`` is what rendering already settled on (their name, or
    "friend" in ``lang``)."""
    from library.languages import entry as language_entry

    cache = {} if cache is None else cache
    values: dict[str, str | None] = {"first_name": first_name}
    if "language" in needed:
        values["language"] = language_entry(lang).get("native_name") or lang
    if not needed & READER_FACT_TAGS:
        return values
    pk = getattr(profile, "pk", None)
    if pk is None:
        facts: dict = {}
    else:
        if ("facts", pk) not in cache:
            prefetch([pk], cache)
        facts = cache[("facts", pk)]

    book = facts.get("book")
    # The book in the edition they read it in, which may not be the email's language.
    values["last_book"] = _title(cache, "Book", book[0], book[1]) if book else None
    finished = facts.get("finished", 0)
    values["books_finished"] = str(finished) if finished else None
    plan = facts.get("plan")
    values["plan_name"] = values["plan_day"] = None
    if plan:
        slug, done = plan
        title = _title(cache, "Plan", slug, lang)
        if title:
            values["plan_name"] = title
            total = _plan_length(cache, slug, lang)
            if done < total:
                values["plan_day"] = str(done + 1)
    return values


def sample_values(lang: str) -> dict[str, str | None]:
    """A made-up reader with everything — for previews."""
    values = {key: tag.sample for key, tag in TAGS.items()}
    from library.languages import entry as language_entry

    values["language"] = language_entry(lang).get("native_name") or lang
    return values


def default_for(key: str, lang: str) -> str | None:
    """A tag's own default when the reader has no value (step 2 above)."""
    if key == "first_name":
        return copy_mod.FRIEND.get(copy_mod.base_lang(lang), copy_mod.FRIEND["en"])
    return None


# --- Filling ----------------------------------------------------------------------


class _Missing(Exception):
    """A tag with no value, no fallback and no default."""


def _fill_one(text: str, values: dict, lang: str) -> str:
    def sub(m: re.Match) -> str:
        key = tag_key(m.group(1))
        if key is None:
            return m.group(0)  # not ours: leave it (preflight flags it)
        value = values.get(key)
        if value:
            return value
        if m.group(2) is not None:
            return m.group(2).strip()
        default = default_for(key, lang)
        if default:
            return default
        raise _Missing(key)

    return TAG.sub(sub, text)


def fill_line(text: str, values: dict, lang: str) -> str | None:
    """Fill a one-line field (a heading, a label, a caption); ``None`` when a
    tag in it has nothing to say — the field is left out."""
    try:
        return _fill_one(text, values, lang)
    except _Missing:
        return None


def fill_paragraph(text: str, values: dict, lang: str) -> str:
    """Fill a paragraph, leaving out each sentence with a tag that has nothing
    to say (step 3 above). Line breaks inside it are kept."""
    if not TAG.search(text):
        return text
    kept = []
    for sentence in _SENTENCE.findall(text):
        filled = fill_line(sentence, values, lang)
        if filled is not None:
            kept.append(filled)
    return "".join(kept).strip()


def fill_subject(text: str, values: dict, lang: str) -> str:
    """Fill a subject line: a tag with nothing to say is dropped, and the
    punctuation it leaves dangling tidied."""
    if not TAG.search(text):
        return text

    def sub(m: re.Match) -> str:
        try:
            return _fill_one(m.group(0), values, lang)
        except _Missing:
            return ""

    out = TAG.sub(sub, text)
    out = re.sub(r"\s+([,.!?:;])", r"\1", out)  # "going ," → "going,"
    out = re.sub(r"[,;:]+([.!?])", r"\1", out)  # "going,!" → "going!"
    out = re.sub(r"^[\s,.:;–—-]+|[\s,;:–—-]+$", "", out)
    return re.sub(r"\s{2,}", " ", out).strip()
