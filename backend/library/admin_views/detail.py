"""Admin dashboard API — per-work detail and library export."""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import allowed_languages, requires

from .. import dropoff, invalidation, job_status
from ..audit import AdminAudited
from ..corrections import COPYRIGHT_BLOCKED_SLUGS, RETIRED_BOOKS
from ..languages import target_codes
from ..models import (
    AdminAction,
    Author,
    Book,
    Plan,
    Quote,
    ReviewOutcome,
    Sermon,
    TopicSermon,
)
from ..qa import chapter_flags
from ..views import _language_entry


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminBookDetailView(APIView):
    """A single canonical work across all its languages, for the admin.

    Each language row carries its metadata (source, cover, links) and its
    chapter list with word counts and quality flags (see ``chapter_flags``).
    English is listed first.
    """


    def get(self, request, slug):
        books = list(Book.objects.filter(slug=slug).select_related("author"))
        if not books:
            return Response({"detail": "No such work."}, status=404)
        canonical = next((b for b in books if b.language == "en"), books[0])

        # Every edition's progress rows in one query, for its "where readers
        # stop" curve (library.dropoff).
        progress = dropoff.progress_rows(slugs=[slug])

        languages = []
        for b in sorted(books, key=lambda x: (x.language != "en", x.language)):
            rows = list(
                b.chapters.order_by("order").values(
                    "order", "title", "word_count", "body_text", "body_html"
                )
            )
            max_order = max((r["order"] for r in rows), default=0)
            chapters = []
            for r in rows:
                chapters.append(
                    {
                        "order": r["order"],
                        "title": r["title"],
                        "word_count": r["word_count"] or 0,
                        "flags": chapter_flags(
                            r["title"], r["word_count"] or 0,
                            r["body_text"], r["body_html"],
                            r["order"] < max_order,
                        ),
                    }
                )
            curve = dropoff.reach(progress.get((slug, b.language), []), [c["order"] for c in chapters])
            languages.append(
                {
                    **_language_entry(b.language),
                    "title": b.title,
                    "subtitle": b.subtitle,
                    "description": b.description,
                    "hook": b.hook,
                    "source_type": b.source_type,
                    "is_published": b.is_published,
                    "sort_order": b.sort_order,
                    "cover_url": b.cover_url,
                    "cover_color": b.cover_color,
                    "source_url": b.source_url,
                    "pdf_url": b.pdf_url,
                    "word_count": sum(ch["word_count"] for ch in chapters),
                    "chapters": chapters,
                    # Where readers stop: per-chapter reach, and the chapter
                    # that loses the largest share of its readers.
                    "reach": curve,
                    "steepest": dropoff.steepest_drop(
                        curve, min_readers=dropoff.MIN_READERS_BOOK
                    ),
                }
            )

        return Response(
            {
                "slug": slug,
                "title": canonical.title,
                "author": {
                    "name": canonical.author.name,
                    "slug": canonical.author.slug,
                    "id": canonical.author_id,
                },
                "languages": languages,
                "untranslated": _untranslated("book", slug, {b.language for b in books}),
                "stall_days": dropoff.STALL_DAYS,
            }
        )


#: A language with no edition and no job ever filed: nothing to report but the gap.
NOT_FILED = "none"


def _untranslated(type_: str, slug: str, present: set[str]) -> dict:
    """Every target language with no edition of this work, and where its
    translation job stands — so the work's page answers "what's missing, and
    is anyone on it?" without a trip to the coverage matrix.

    ``blocked`` is the copyright rule (``jobs.translation_blocked``): no job may
    be filed, so the client shows the gap without a Translate button. A
    language whose job was never filed (no ``translation.job`` row, nothing in
    the open queue) reads ``none``; the rest are ``job_status`` stages, with the
    issue or PR to open when GitHub named one.
    """
    from .jobs import translation_blocked

    codes = [c for c in target_codes() if c not in present]
    keys = {(type_, slug, c): None for c in codes}
    filed: dict[str, object] = {}
    for target, at in (
        AdminAction.objects.filter(
            action=AdminAction.Action.TRANSLATION_JOB,
            target__in=[job_status.target_of(k) for k in keys],
        )
        .order_by("at")
        .values_list("target", "at")
    ):
        filed[target] = at  # ascending, so the latest filing wins
    for k in keys:
        keys[k] = filed.get(job_status.target_of(k))
    queue = None

    def read_queue():
        nonlocal queue
        queue = job_status.open_jobs()
        return queue

    status = job_status.statuses(keys, read_queue) if keys else {}
    rows = []
    for key in keys:
        stage = status.get(key, job_status.UNKNOWN)
        q = queue if isinstance(queue, job_status.Queue) else None
        in_queue = q is not None and key in q.jobs
        # Never filed from here and not in the queue: "closed" would be a guess
        # about a job that doesn't exist.
        if keys[key] is None and not in_queue and stage in (job_status.CLOSED, job_status.UNKNOWN):
            stage = NOT_FILED
        rows.append(
            {
                **_language_entry(key[2]),
                "job_status": stage,
                "issue_url": q.jobs[key].get("url") or None if in_queue else None,
                "pr_url": q.pr_for(key) if q and stage == job_status.PR_OPEN else None,
            }
        )
    return {"blocked": translation_blocked(type_, slug), "languages": rows}


def publish_refusal(model, slug: str, published: bool) -> str | None:
    """Why ``slug`` may not be published, or None. Only publishing is ever
    refused — unpublishing stays open (it is the takedown lever).

    A publish grant is not a rights clearance (``COPYRIGHT_BLOCKED_SLUGS``), and
    a retired duplicate's URLs forward to its successor (``RETIRED_BOOKS``), so
    a published edition of one would be unreachable. Books only: neither list
    names a sermon. Shared by the one-edition toggle and the bulk endpoint."""
    if not published or model is not Book:
        return None
    if slug in COPYRIGHT_BLOCKED_SLUGS:
        return f"“{slug}” is under copyright and cannot be published."
    if slug in RETIRED_BOOKS:
        return (
            f"“{slug}” is retired as a duplicate of “{RETIRED_BOOKS[slug][0]}” "
            "and cannot be published."
        )
    return None


@requires(AdminCapability.PUBLISH, verb=AdminVerb.ACT, language_arg="language")
class _EditionPublishView(AdminAudited, APIView):
    """Publish or unpublish one language edition of a per-language work.

    ``is_published`` is the reader-visibility switch — the public API filters on
    it, so unpublishing removes the edition from the site immediately, and it is
    the lever an urgent copyright takedown pulls. It is deliberately
    **create-only** in the seed (``CREATE_ONLY_FIELDS``), so a decision made here
    is never walked back by a deploy re-seeding from the fixture.

    ``POST /api/admin/<works>/<slug>/publish/`` with ``{language, published}``.
    Scoped to a single ``(slug, language)`` row — the admin detail page toggles
    one edition at a time. Prerendered SEO pages catch up on the throttled
    rebuild ``mark_content_changed`` triggers, the same path import-publish uses.

    Subclasses set ``model`` (Book/Sermon) and ``target_kind`` (the audit-target
    prefix); ``save(update_fields=["is_published"])`` is load-bearing on both —
    a bare ``save()`` would re-tokenise every chapter/body for the search index.
    """

    model = None
    target_kind = ""

    def audit_action_for(self, request):
        return (
            AdminAction.Action.CONTENT_PUBLISH
            if self._parse(request.data)[1]
            else AdminAction.Action.CONTENT_UNPUBLISH
        )

    @staticmethod
    def _parse(data) -> tuple[str, bool]:
        """``(language, published)`` from the request body. ``published``
        defaults to True so a bare press publishes rather than silently toggling
        to an unintended state."""
        language = (data.get("language") or "").strip()
        published = data.get("published")
        return language, True if published is None else bool(published)

    def audit_entry(self, request, response):
        # finalize_response only records on a 2xx, and post() always returns
        # these three keys there — so no defensive fallbacks are reachable.
        d = response.data
        return f"{self.target_kind}:{d['slug']}:{d['language']}", {
            "is_published": d["is_published"]
        }

    def post(self, request, slug):
        language, published = self._parse(request.data)
        if not language:
            return Response({"detail": "A language is required."}, status=400)
        refusal = publish_refusal(self.model, slug, published)
        if refusal:
            return Response({"detail": refusal}, status=409)
        obj = self.model.objects.filter(slug=slug, language=language).first()
        if obj is None:
            return Response(
                {"detail": f"No {language} edition of “{slug}”."}, status=404
            )
        if obj.is_published != published:
            obj.is_published = published
            obj.save(update_fields=["is_published"])
            # Reader-visible now on the SPA (the API filters is_published); the
            # prerendered pages follow on the throttled rebuild.
            invalidation.mark_content_changed()
        return Response(
            {"slug": obj.slug, "language": obj.language, "is_published": obj.is_published}
        )


class AdminBookPublishView(_EditionPublishView):
    """Publish/unpublish one book edition (see :class:`_EditionPublishView`)."""

    model = Book
    target_kind = "book"


class AdminSermonPublishView(_EditionPublishView):
    """Publish/unpublish one sermon edition (see :class:`_EditionPublishView`)."""

    model = Sermon
    target_kind = "sermon"


#: How many editions one bulk request may touch — a page of a list, not the library.
BULK_PUBLISH_MAX = 200
_BULK_MODELS = {"book": Book, "sermon": Sermon}


@requires(AdminCapability.PUBLISH, verb=AdminVerb.ACT)
class AdminBulkPublishView(AdminAudited, APIView):
    """Publish or unpublish many editions at once, from the admin lists.

    ``POST /api/admin/publish/bulk/`` with ``{kind: book|sermon, published,
    items: [{slug, language}]}``. Each item is held to the same rules as the
    one-edition toggle (:class:`_EditionPublishView`): the caller's publish
    grant must cover its language, and :func:`publish_refusal` applies. An item
    that fails one is skipped with its reason rather than failing the batch —
    the answer is 207 when any was. One ``mark_content_changed`` for the lot,
    and one audit row per edition that actually changed (``audit_entries``), so
    each edition's History shows it.
    """

    def audit_action_for(self, request):
        return (
            AdminAction.Action.CONTENT_PUBLISH
            if _EditionPublishView._parse(request.data)[1]
            else AdminAction.Action.CONTENT_UNPUBLISH
        )

    def audit_entries(self, request, response):
        kind = response.data["kind"]
        published = response.data["published"]
        return [
            (f"{kind}:{i['slug']}:{i['language']}", {"is_published": published, "bulk": True})
            for i in response.data["changed"]
        ]

    def post(self, request):
        kind = str(request.data.get("kind", "")).strip()
        model = _BULK_MODELS.get(kind)
        if model is None:
            return Response({"detail": "kind must be book or sermon."}, status=400)
        items = request.data.get("items")
        if not isinstance(items, list) or not items:
            return Response({"detail": "items must be a non-empty list."}, status=400)
        if len(items) > BULK_PUBLISH_MAX:
            return Response(
                {"detail": f"At most {BULK_PUBLISH_MAX} editions at a time."}, status=400
            )
        published = _EditionPublishView._parse(request.data)[1]
        allowed = allowed_languages(request, AdminCapability.PUBLISH, AdminVerb.ACT)

        if not all(isinstance(raw, dict) for raw in items):
            return Response({"detail": "each item must be {slug, language}."}, status=400)

        wanted: dict[tuple[str, str], dict] = {}
        skipped = []
        for raw in items:
            slug = str(raw.get("slug") or "").strip()
            language = str(raw.get("language") or "").strip()
            item = {"slug": slug, "language": language}
            if not slug or not language:
                # Reported, not dropped: the caller's "N published" must add up.
                skipped.append({**item, "reason": "Needs both a slug and a language."})
                continue
            if (slug, language) in wanted:
                continue  # the same edition twice is one edition
            if allowed is not None and language not in allowed:
                skipped.append({**item, "reason": "Your publish access doesn't cover this language."})
            elif refusal := publish_refusal(model, slug, published):
                skipped.append({**item, "reason": refusal})
            else:
                wanted[(slug, language)] = item

        # One read for every edition asked about, one write for those that flip.
        # update(), not save(): is_published derives nothing, and a Sermon's
        # save() re-parses its whole body — 200 of them was seconds of work.
        match = Q(pk__in=[])
        for slug, language in wanted:
            match |= Q(slug=slug, language=language)
        rows = {
            (r["slug"], r["language"]): r
            for r in model.objects.filter(match).values("pk", "slug", "language", "is_published")
        }
        changed, unchanged, flip = [], [], []
        for key, item in wanted.items():
            row = rows.get(key)
            if row is None:
                skipped.append({**item, "reason": "No such edition."})
            elif row["is_published"] == published:
                unchanged.append(item)
            else:
                changed.append(item)
                flip.append(row["pk"])
        if flip:
            model.objects.filter(pk__in=flip).update(is_published=published)
        if changed:
            invalidation.mark_content_changed()
        return Response(
            {
                "kind": kind,
                "published": published,
                "changed": changed,
                "unchanged": unchanged,
                "skipped": skipped,
            },
            status=207 if skipped else 200,
        )


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSermonDetailView(APIView):
    """A single canonical sermon across all its languages, for the admin.

    The sermon counterpart to :class:`AdminBookDetailView`, minus chapters — a
    sermon is a single body, so each language row carries its metadata, its
    study material (summary, main points, Q&A), an opening excerpt, its quotes
    and review state, and the publish state the toggle acts on. The work as a
    whole carries its topics and the languages it is still missing. English is
    listed first.
    """

    #: How much of the body a row previews — enough to recognise the text.
    EXCERPT_CHARS = 600


    def get(self, request, slug):
        sermons = list(Sermon.objects.filter(slug=slug).select_related("author"))
        if not sermons:
            return Response({"detail": "No such sermon."}, status=404)
        canonical = next((s for s in sermons if s.language == "en"), sermons[0])

        quotes = dict(
            Quote.objects.filter(sermon__slug=slug)
            .values("sermon__language")
            .annotate(n=Count("pk"))
            .values_list("sermon__language", "n")
        )
        reviews = {
            r.language: r
            for r in ReviewOutcome.objects.filter(kind=ReviewOutcome.Kind.SERMON, slug=slug)
        }

        def excerpt(text: str) -> str:
            from ..search import to_word_end

            text = " ".join((text or "").split())
            if len(text) <= self.EXCERPT_CHARS:
                return text
            return f"{to_word_end(text, self.EXCERPT_CHARS, 0)}…"

        def review(language: str) -> dict | None:
            r = reviews.get(language)
            if r is None:
                return None
            return {
                "outcome": r.outcome,
                "confirmed": r.confirmed_at is not None,
                "note": r.note,
                "decided_at": r.decided_at.isoformat(),
            }

        languages = [
            {
                **_language_entry(s.language),
                "title": s.title,
                "scripture_ref": s.scripture_ref,
                "preached_on": s.preached_on.isoformat() if s.preached_on else None,
                "source_type": s.source_type,
                "is_published": s.is_published,
                "word_count": s.word_count,
                "source_url": s.source_url,
                "attribution": s.attribution,
                "summary": s.summary,
                "main_points": s.main_points or [],
                "study_questions": s.study_questions or [],
                "excerpt": excerpt(s.body_text),
                "quotes": quotes.get(s.language, 0),
                "review": review(s.language),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sorted(sermons, key=lambda x: (x.language != "en", x.language))
        ]
        topics = [
            {"slug": t.topic.slug, "title": t.topic.title}
            for t in TopicSermon.objects.filter(sermon_slug=slug)
            .select_related("topic")
            .order_by("topic__title")
        ]
        return Response(
            {
                "slug": slug,
                "title": canonical.title,
                "author": {"name": canonical.author.name, "slug": canonical.author.slug},
                "languages": languages,
                "topics": topics,
                "untranslated": _untranslated("sermon", slug, {s.language for s in sermons}),
            }
        )


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminExportView(APIView):
    """Download the full content inventory as JSON (default) or CSV.

    ``?format=csv`` streams a flat one-row-per-item table (books, sermons,
    plans); otherwise a structured JSON object (books, sermons, plans, authors)
    for offline analysis or reporting. Admin-gated.
    """


    def get(self, request):
        data = self._inventory()
        # Note: not "format" — DRF reserves that query param for renderer
        # negotiation, so ?format=csv would 404 before reaching here.
        if request.query_params.get("fmt", "").lower() == "csv":
            return self._csv(data)
        return Response(data)

    def _inventory(self) -> dict:
        books = [
            {
                "type": "book",
                "slug": b.slug,
                "language": b.language,
                "title": b.title,
                "subtitle": b.subtitle,
                "author": b.author.name,
                "source_type": b.source_type,
                "is_published": b.is_published,
                "chapters": b.num_chapters,
                "words": b.words or 0,
                "source_url": b.source_url,
            }
            for b in Book.objects.select_related("author")
            .annotate(num_chapters=Count("chapters"), words=Sum("chapters__word_count"))
            .order_by("slug", "language")
        ]
        sermons = [
            {
                "type": "sermon",
                "slug": s.slug,
                "language": s.language,
                "title": s.title,
                "author": s.author.name,
                "is_published": s.is_published,
                "words": s.word_count,
                "source_url": s.source_url,
            }
            for s in Sermon.objects.select_related("author").order_by("slug", "language")
        ]
        plans = [
            {
                "type": "plan",
                "slug": p.slug,
                "language": p.language,
                "title": p.title,
                "is_published": p.is_published,
                "days": p.num_days,
            }
            for p in Plan.objects.annotate(num_days=Count("days")).order_by(
                "slug", "language"
            )
        ]
        authors = [
            {
                "slug": a.slug,
                "name": a.name,
                "birth_year": a.birth_year,
                "death_year": a.death_year,
                "has_bio": bool(a.bio),
                "has_bio_html": bool(a.bio_html),
            }
            for a in Author.objects.order_by("name")
        ]
        return {"books": books, "sermons": sermons, "plans": plans, "authors": authors}

    def _csv(self, data: dict):
        import csv
        import io

        from django.utils import timezone

        from .csv_export import csv_response, csv_safe

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["type", "slug", "language", "title", "author", "source_type",
             "published", "chapters_or_days", "words", "source_url"]
        )
        # csv_safe on the free-text cells (title, author, source_url); the slug,
        # language, numeric and boolean columns are constrained and left as-is.
        for b in data["books"]:
            writer.writerow(
                ["book", b["slug"], b["language"], csv_safe(b["title"]),
                 csv_safe(b["author"]), b["source_type"], b["is_published"],
                 b["chapters"], b["words"], csv_safe(b["source_url"])]
            )
        for s in data["sermons"]:
            writer.writerow(
                ["sermon", s["slug"], s["language"], csv_safe(s["title"]),
                 csv_safe(s["author"]), "", s["is_published"], "", s["words"],
                 csv_safe(s["source_url"])]
            )
        for p in data["plans"]:
            writer.writerow(
                ["plan", p["slug"], p["language"], csv_safe(p["title"]), "", "",
                 p["is_published"], p["days"], "", ""]
            )
        stamp = timezone.now().date().isoformat()
        return csv_response(buf.getvalue(), f"ochorus-inventory-{stamp}.csv")
