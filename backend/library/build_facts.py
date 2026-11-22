"""The production-only facts a reader build needs, as one small JSON document.

The web build prerenders every public page from the API. Normally that is the
live production API, and crawling it is what knocked the 512 MB instance over
on 2026-11-16..19. The alternative (docs/build-without-prod-api.md) is a
throwaway API seeded from this checkout — but a DB rebuilt from the repo is not
the production DB. The seeds make some fields **create-only** precisely so that
a workflow acting on the live DB owns them afterwards, and those decisions exist
nowhere in the repo:

* ``Language`` — which languages are live (an admin presses Go live), their
  names and Bible credit as edited in the admin, and languages added from the
  admin at all (``seed_languages`` never touches those).
* ``is_published`` on books, sermons, articles — an admin publish toggle or an
  urgent copyright unpublish.
* ``source_type`` on the same — review approval (``approve_translation``, the
  review queue). Never shown to readers, but it decides which translated
  chapters the sitemap and hreflang offer to search engines.
* ``Quote.reviewed`` — ``approve_quotes`` and takedowns in the live DB.
* ``AuthorTranslation`` rows a native reviewer approved: ``seed_author_translations``
  never rewrites their wording, so production keeps the approved text while the
  repo's file may have moved on.
* ``is_published`` on plans and topics, for completeness (create-only in their
  seeds too).

``export_facts`` reads those from whatever DB it runs against (production, in
the deploy train); ``apply_facts`` lays them over a DB freshly seeded from the
repo. Only rows that exist on BOTH sides are touched: a row the repo just added
keeps the value its seed creates it with — exactly what production's own
``release`` will give it — and a row only production has (an admin upload that
never reached the fixture) is reported, because no overlay of a few fields can
recreate a whole work.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import (
    Article,
    AuthorTranslation,
    Book,
    Language,
    Plan,
    Quote,
    Sermon,
    Topic,
)
from .sanitize import clean_bio_html

FORMAT = "ochorus-build-facts"
VERSION = 1

#: Language columns an admin can set and the build can see. The readiness
#: thresholds, glossary and notes are admin-only and never reach a page.
LANGUAGE_FIELDS = (
    "name",
    "native_name",
    "bible_code",
    "bible_label",
    "bible_licence",
    "bible_attribution",
    "rtl",
    "is_source",
    "status",
    "sort_order",
)

#: (facts key, model) for the per-language editions with both create-only fields.
EDITION_MODELS = (("books", Book), ("sermons", Sermon), ("articles", Article))


def export_facts() -> dict:
    """Everything ``apply_facts`` needs, read from the current DB."""
    facts: dict = {
        "format": FORMAT,
        "version": VERSION,
        "exported_at": timezone.now().isoformat(),
        "languages": [
            {
                "code": lang.code,
                **{f: getattr(lang, f) for f in LANGUAGE_FIELDS},
                "went_live_at": lang.went_live_at.isoformat() if lang.went_live_at else None,
            }
            for lang in Language.objects.order_by("code")
        ],
    }
    for key, model in EDITION_MODELS:
        facts[key] = [
            [slug, language, published, source_type]
            for slug, language, published, source_type in model.objects.order_by(
                "slug", "language"
            ).values_list("slug", "language", "is_published", "source_type")
        ]
    facts["plans"] = [
        list(row)
        for row in Plan.objects.order_by("slug", "language").values_list(
            "slug", "language", "is_published"
        )
    ]
    facts["topics"] = [
        list(row) for row in Topic.objects.order_by("slug").values_list("slug", "is_published")
    ]
    facts["quotes"] = [
        list(row) for row in Quote.objects.order_by("slug").values_list("slug", "reviewed")
    ]
    # Only REVIEWED rows: an unreviewed row's text is whatever the repo's file
    # says, which the local seed reproduces by itself. A reviewed row's text is
    # the approver's, and the seed deliberately never rewrites it.
    facts["reviewed_author_translations"] = [
        {
            "author": tr.author.slug,
            "language": tr.language,
            "bio": tr.bio,
            "bio_html": tr.bio_html,
            "faq": tr.faq,
            "source_stale": tr.source_stale,
        }
        for tr in AuthorTranslation.objects.filter(reviewed=True)
        .select_related("author")
        .order_by("author__slug", "language")
    ]
    return facts


def validate(facts) -> None:
    """Raise ValueError unless ``facts`` is a document this module wrote."""
    if not isinstance(facts, dict) or facts.get("format") != FORMAT:
        raise ValueError(f"not an {FORMAT} document")
    if facts.get("version") != VERSION:
        raise ValueError(
            f"{FORMAT} version {facts.get('version')!r}; this checkout reads {VERSION}"
        )
    codes = [row.get("code") for row in facts.get("languages") or []]
    if "en" not in codes:
        # English is the source language. A document without it was read from
        # the wrong database — applying it would take every page's locale away.
        raise ValueError("no English row in languages — exported from the wrong database?")


def _apply_flags(model, rows, key_fields, value_fields, report, label) -> None:
    """Set ``value_fields`` on each existing row named by ``rows``.

    ``rows`` are lists: the key values then the field values. Rows missing
    locally are counted under ``report["missing"][label]`` (production-only
    content); rows present locally but absent from the facts are left alone
    (content this checkout adds, which production's release will create with
    the same seed default)."""
    wanted = {tuple(r[: len(key_fields)]): r[len(key_fields) :] for r in rows}
    changed = 0
    present = set()
    for obj in model.objects.only("pk", *key_fields, *value_fields):
        key = tuple(getattr(obj, f) for f in key_fields)
        if key not in wanted:
            continue
        present.add(key)
        values = dict(zip(value_fields, wanted[key], strict=True))
        if all(getattr(obj, f) == v for f, v in values.items()):
            continue
        # A scoped UPDATE, not save(): these are flags, and save() would
        # rebuild the search vector and move updated_at for nothing.
        model.objects.filter(pk=obj.pk).update(**values)
        changed += 1
    report["changed"][label] = changed
    missing = sorted(k for k in wanted if k not in present)
    if missing:
        report["missing"][label] = [":".join(map(str, k)) for k in missing]


@transaction.atomic
def apply_facts(facts: dict) -> dict:
    """Lay ``facts`` over the current DB. Returns a report:

    ``{"changed": {label: n}, "missing": {label: [keys]}, "languages": {...}}``
    where ``missing`` lists what production has and this DB does not.
    """
    validate(facts)
    report: dict = {"changed": {}, "missing": {}}

    created, updated = [], []
    for row in facts["languages"]:
        values = {f: row[f] for f in LANGUAGE_FIELDS if f in row}
        values["went_live_at"] = row.get("went_live_at")
        _, was_created = Language.objects.update_or_create(code=row["code"], defaults=values)
        (created if was_created else updated).append(row["code"])
    # A language this checkout seeds but production never had (a new entry in
    # language_seed.py, not yet deployed) is not live there; keep it dark here.
    known = {row["code"] for row in facts["languages"]}
    darkened = list(
        Language.objects.exclude(code__in=known)
        .filter(status=Language.Status.LIVE)
        .values_list("code", flat=True)
    )
    if darkened:
        Language.objects.filter(code__in=darkened).update(status=Language.Status.DRAFT)
    report["languages"] = {
        "live": list(
            Language.objects.filter(status=Language.Status.LIVE)
            .order_by("sort_order", "name")
            .values_list("code", flat=True)
        ),
        "created": created,
        "darkened": darkened,
    }

    for key, model in EDITION_MODELS:
        _apply_flags(
            model,
            facts.get(key) or [],
            ("slug", "language"),
            ("is_published", "source_type"),
            report,
            key,
        )
    _apply_flags(Plan, facts.get("plans") or [], ("slug", "language"), ("is_published",), report, "plans")
    _apply_flags(Topic, facts.get("topics") or [], ("slug",), ("is_published",), report, "topics")
    _apply_flags(Quote, facts.get("quotes") or [], ("slug",), ("reviewed",), report, "quotes")

    changed = 0
    missing = []
    for row in facts.get("reviewed_author_translations") or []:
        n = AuthorTranslation.objects.filter(
            author__slug=row["author"], language=row["language"]
        ).update(
            reviewed=True,
            bio=row.get("bio", ""),
            # Sanitized at this write path like every other (backend/CLAUDE.md);
            # the export came from a DB that already holds clean HTML, so this
            # changes entity spelling at most, never what renders.
            bio_html=clean_bio_html(row.get("bio_html") or ""),
            faq=row.get("faq") or [],
            source_stale=bool(row.get("source_stale")),
        )
        if n:
            changed += n
        else:
            missing.append(f"{row['author']}:{row['language']}")
    report["changed"]["reviewed_author_translations"] = changed
    if missing:
        report["missing"]["reviewed_author_translations"] = missing
    return report
