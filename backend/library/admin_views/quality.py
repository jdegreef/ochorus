"""Admin dashboard API — content quality (review queue, audit heuristics)."""

from __future__ import annotations

import re
from html import unescape

from django.db import transaction
from django.db.models import Count, Max
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    PlanDay,
    ReviewOutcome,
    Sermon,
    TranslationNote,
)
from ..qa import (
    FRAG_MAX_AVG,
    FRAG_MIN_PARAS,
    FRAG_MIN_WORDS,
    GENERIC_TITLE,
    GIANT_MIN,
    TERMINAL_PUNCT,
    TINY_MAX,
    translation_flags,
)


class AdminReviewQueueView(APIView):
    """The AI-translation review queue.

    GET lists everything awaiting a native-speaker check — books and sermons
    (``source_type`` ai_unreviewed) and author bios (``AuthorTranslation``
    ``reviewed`` False) — filtered, faceted and paged. POST records a decision
    for one item or a batch; DELETE undoes one.

    Sermons were absent from this queue until now while 74 of them shipped
    unreviewed, more than the books that *were* listed: the reader showed an
    "awaiting native review" badge that this screen gave no way to act on, and
    clearing the queue implied a backlog that was empty when it was not.

    Approving still flips the original field (``source_type`` →  ai_reviewed, or
    ``reviewed`` → True) exactly as the approve_* management commands do, so
    nothing downstream changes. The decision itself is additionally recorded in
    ``ReviewOutcome``, which is what makes it undoable, attributable, and able to
    express "needs work" — a state the original booleans cannot hold.
    """

    permission_classes = [IsAdminEmail]

    KINDS = ("book", "sermon", "bio")
    PAGE_SIZE = 25

    # ---- read ---------------------------------------------------------------

    def get(self, request):
        q = request.query_params
        kind = q.get("kind") or ""
        language = q.get("language") or ""
        outcome = q.get("outcome") or ""
        flagged_only = q.get("flagged") in ("1", "true", "yes")
        sort = q.get("sort") or "oldest"

        rows = self._rows()
        decided = self._outcomes()
        notes = self._note_summary()
        noted = set(notes)

        # A row is "flagged" when the pipeline recorded a verse it had to render
        # itself. That list is the actual review task, and it is the one thing a
        # reviewer cannot discover by reading the translation fluently.
        for r in rows:
            k = (r["kind"], r["slug"], r["language"])
            r["outcome"] = decided.get(k)
            r["notes"] = notes.get(k, {"mined": 0, "self_rendered": 0, "references": []})
            r["provenance"] = self._provenance(notes.get(k))
            r["flagged"] = r["notes"]["self_rendered"] > 0
            # Distinguish "examined and clean" from "never examined" — the UI
            # must not render an absence of notes as an absence of problems.
            r["notes_recorded"] = k in noted

        # Facets are computed over everything still awaiting a decision, so the
        # counts a reviewer navigates by never shift when a filter is applied.
        undecided = [r for r in rows if not r["outcome"]]
        facets = {
            "language": _tally(undecided, "language"),
            "kind": _tally(undecided, "kind"),
        }

        if outcome == "needs_work":
            sel = [r for r in rows if r["outcome"] and r["outcome"]["outcome"] == "needs_work"]
        else:
            sel = undecided
        if kind in self.KINDS:
            sel = [r for r in sel if r["kind"] == kind]
        if language:
            sel = [r for r in sel if r["language"] == language]
        if flagged_only:
            sel = [r for r in sel if r["flagged"]]

        if sort == "flagged":
            sel.sort(key=lambda r: (-r["notes"]["self_rendered"], r["language"], r["title"]))
        elif sort == "largest":
            sel.sort(key=lambda r: -(r.get("words") or 0))
        else:  # oldest — the fairest proxy for neglect
            sel.sort(key=lambda r: (r.get("created_at") or "", r["language"], r["title"]))

        try:
            page = max(1, int(q.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        pages = max(1, (len(sel) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        page = min(page, pages)
        start = (page - 1) * self.PAGE_SIZE
        window = sel[start : start + self.PAGE_SIZE]

        # Mechanical checks are computed for the PAGE only. They need both
        # editions' bodies, so doing it for the whole library on every request
        # would read hundreds of rows to render twenty-five.
        self._attach_flags(window)

        return Response(
            {
                "results": window,
                "total": len(undecided),
                "filtered": len(sel),
                "flagged_total": sum(1 for r in undecided if r["flagged"]),
                "needs_work_total": sum(
                    1 for r in rows if r["outcome"] and r["outcome"]["outcome"] == "needs_work"
                ),
                "page": page,
                "pages": pages,
                "page_size": self.PAGE_SIZE,
                "facets": facets,
            }
        )

    def _rows(self) -> list[dict]:
        out: list[dict] = []
        books = (
            Book.objects.filter(source_type=Book.SourceType.AI_UNREVIEWED)
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .order_by("language", "sort_order", "title")
        )
        for b in books:
            out.append(
                {
                    "kind": "book",
                    "slug": b.slug,
                    "language": b.language,
                    "title": b.title,
                    "author": b.author.name,
                    "chapters": b.num_chapters,
                    "words": None,
                    "scripture_ref": "",
                    "created_at": b.created_at.isoformat() if b.created_at else "",
                }
            )
        sermons = (
            Sermon.objects.filter(source_type=Book.SourceType.AI_UNREVIEWED)
            .select_related("author")
            .order_by("language", "sort_order", "title")
        )
        for s in sermons:
            out.append(
                {
                    "kind": "sermon",
                    "slug": s.slug,
                    "language": s.language,
                    "title": s.title,
                    "author": s.author.name,
                    "chapters": None,
                    "words": s.word_count,
                    "scripture_ref": s.scripture_ref,
                    "created_at": s.created_at.isoformat() if s.created_at else "",
                }
            )
        bios = (
            AuthorTranslation.objects.filter(reviewed=False)
            .exclude(bio="", bio_html="")
            .select_related("author")
            .order_by("language", "author__name")
        )
        for t in bios:
            out.append(
                {
                    "kind": "bio",
                    "slug": t.author.slug,
                    "language": t.language,
                    "title": t.author.name,
                    "author": t.author.name,
                    "chapters": None,
                    "words": len((t.bio_html or t.bio or "").split()),
                    "scripture_ref": "",
                    "has_short": bool(t.bio),
                    "has_long": bool(t.bio_html),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                }
            )
        return out

    def _outcomes(self) -> dict:
        return {
            (o.kind, o.slug, o.language): {
                "outcome": o.outcome,
                "note": o.note,
                "reviewer": o.reviewer,
                "decided_at": o.decided_at.isoformat(),
            }
            for o in ReviewOutcome.objects.all()
        }

    def _note_summary(self) -> dict:
        out: dict = {}
        for n in TranslationNote.objects.all():
            k = (n.kind, n.slug, n.language)
            e = out.setdefault(
                k,
                {"mined": 0, "self_rendered": 0, "references": [], "job": None, "pr": None},
            )
            if n.status == TranslationNote.Status.SELF_RENDERED:
                e["self_rendered"] += 1
                e["references"].append(
                    {
                        "reference": n.reference,
                        "block_index": n.block_index,
                        "status": n.status,
                    }
                )
            else:
                e["mined"] += 1
            e["job"] = e["job"] or n.job_issue
            e["pr"] = e["pr"] or n.pull_request
        return out

    @staticmethod
    def _provenance(note: dict | None) -> dict | None:
        if not note or not (note.get("job") or note.get("pr")):
            return None
        return {"job_issue": note.get("job"), "pull_request": note.get("pr")}

    def _attach_flags(self, rows: list[dict]) -> None:
        """Mechanical source-vs-translation checks for the visible page."""
        for r in rows:
            source, target = self._bodies(r)
            if source is None or target is None:
                r["flags"] = None
                continue
            r["flags"] = translation_flags(
                source, target, language=r["language"], kind=r["kind"]
            )

    @staticmethod
    def _bodies(row: dict) -> tuple[str | None, str | None]:
        """The English source body and the translated body, or (None, None)."""
        kind, slug, lang = row["kind"], row["slug"], row["language"]
        if kind == "book":
            # A book's text lives in its chapters; concatenate in order so the
            # tag sequence covers the whole edition.
            def joined(language):
                qs = Chapter.objects.filter(book__slug=slug, book__language=language)
                parts = list(qs.order_by("order").values_list("body_html", flat=True))
                return "".join(parts) if parts else None

            return joined("en"), joined(lang)
        if kind == "sermon":
            src = Sermon.objects.filter(slug=slug, language="en").values_list(
                "body_html", flat=True
            ).first()
            tgt = Sermon.objects.filter(slug=slug, language=lang).values_list(
                "body_html", flat=True
            ).first()
            return src, tgt
        author = Author.objects.filter(slug=slug).values_list("bio_html", flat=True).first()
        tr = AuthorTranslation.objects.filter(
            author__slug=slug, language=lang
        ).values_list("bio_html", flat=True).first()
        return author, tr

    # ---- decisions ----------------------------------------------------------

    def post(self, request):
        data = request.data
        items = data.get("items")
        if items is None:
            items = [{k: data.get(k) for k in ("kind", "slug", "language")}]
        if not isinstance(items, list) or not items:
            return Response({"detail": "items must be a non-empty list."}, status=400)
        outcome = data.get("outcome") or ReviewOutcome.Outcome.APPROVED
        if outcome not in ReviewOutcome.Outcome.values:
            return Response(
                {"detail": "outcome must be 'approved' or 'needs_work'."}, status=400
            )
        note = (data.get("note") or "").strip()
        reviewer = getattr(request.user, "email", "") or ""

        # Bulk approval is the one action here that can launder unreviewed
        # content at scale, so eligibility is re-asserted server-side rather
        # than trusted from the client's selection.
        enforce_gate = outcome == ReviewOutcome.Outcome.APPROVED and len(items) > 1
        flagged, has_notes = (
            (self._flagged_keys(), self._noted_keys()) if enforce_gate else (set(), set())
        )

        done, skipped = [], []
        for raw in items:
            kind, slug, language = raw.get("kind"), raw.get("slug"), raw.get("language")
            if kind not in self.KINDS or not slug or not language:
                skipped.append({**raw, "reason": "kind, slug and language are required."})
                continue
            key = (kind, slug, language)
            if enforce_gate and key not in has_notes:
                # FAIL CLOSED. An item with no TranslationNote rows has not been
                # cleared — it has never been examined, which is the opposite of
                # safe. Treating "no data" as "no problems" would let a bulk
                # approve wave through the entire un-noted backlog, which is
                # precisely what this gate exists to prevent.
                skipped.append(
                    {
                        "kind": kind,
                        "slug": slug,
                        "language": language,
                        "reason": "no scripture notes recorded — review individually.",
                    }
                )
                continue
            if key in flagged:
                skipped.append(
                    {
                        "kind": kind,
                        "slug": slug,
                        "language": language,
                        "reason": "has unverified verses — review individually.",
                    }
                )
                continue
            # The field flip and its audit row are ONE unit. Apart, a failure
            # between them approves a translation invisibly: the queue lists only
            # ai_unreviewed rows, so the item vanishes from it with no
            # ReviewOutcome — no reviewer, no reason, and no way to undo from the
            # UI, because undo works off the row that was never written.
            #
            # Per item, not per batch: a 207 that holds back some rows and
            # decides the rest is the documented result, so one bad row must not
            # roll back twenty-four good decisions.
            try:
                with transaction.atomic():
                    err = self._apply(kind, slug, language, outcome)
                    if err:
                        raise _Skip(err)
                    ReviewOutcome.objects.update_or_create(
                        kind=kind,
                        slug=slug,
                        language=language,
                        defaults={"outcome": outcome, "note": note, "reviewer": reviewer},
                    )
            except _Skip as skip:
                # _apply's own refusals (no such translation, public-domain
                # original). Raised rather than returned so the atomic block
                # rolls back instead of committing a flip whose audit row never
                # followed.
                skipped.append(
                    {"kind": kind, "slug": slug, "language": language, "reason": str(skip)}
                )
                continue
            done.append({"kind": kind, "slug": slug, "language": language})

        # 207: a batch where some rows were held back is a normal result, not a
        # failure — one ineligible row must not reject the other twenty-four.
        status = 200 if not skipped else (400 if not done else 207)
        return Response({"ok": not skipped, "decided": done, "skipped": skipped}, status=status)

    def _noted_keys(self) -> set:
        """Items the pipeline has recorded scripture provenance for at all."""
        return {
            (n.kind, n.slug, n.language)
            for n in TranslationNote.objects.only("kind", "slug", "language")
        }

    def _flagged_keys(self) -> set:
        return {
            (n.kind, n.slug, n.language)
            for n in TranslationNote.objects.filter(
                status=TranslationNote.Status.SELF_RENDERED
            ).only("kind", "slug", "language")
        }

    def _apply(self, kind, slug, language, outcome) -> str | None:
        """Flip the underlying field. Returns an error string, or None on success."""
        approving = outcome == ReviewOutcome.Outcome.APPROVED
        if kind in ("book", "sermon"):
            model = Book if kind == "book" else Sermon
            obj = model.objects.filter(slug=slug, language=language).first()
            if obj is None:
                return f"No such {kind} translation."
            # Sermon shares Book's SourceType vocabulary rather than declaring
            # its own, so the enum is read off Book for both.
            if obj.source_type == Book.SourceType.PUBLIC_DOMAIN:
                return f"That {kind} is a public-domain original, not a translation."
            obj.source_type = (
                Book.SourceType.AI_REVIEWED if approving else Book.SourceType.AI_UNREVIEWED
            )
            # Scoped save: source_type is not an indexed field, so this skips the
            # search-vector rebuild that a full save() would trigger.
            obj.save(update_fields=["source_type"])
            return None
        tr = AuthorTranslation.objects.filter(author__slug=slug, language=language).first()
        if tr is None:
            return "No such author-bio translation."
        tr.reviewed = approving
        # Same as approve_author_translation: approval answers staleness.
        if approving:
            tr.source_stale = False
        tr.save(update_fields=["reviewed", "source_stale"])
        return None

    def delete(self, request):
        """Undo a decision, returning the item to the queue."""
        q = request.query_params
        kind, slug, language = q.get("kind"), q.get("slug"), q.get("language")
        if kind not in self.KINDS or not slug or not language:
            return Response(
                {"detail": "kind, slug and language are required."}, status=400
            )
        # Reversing is lossless: ai_reviewed → ai_unreviewed restores exactly the
        # state the fixture ships, and seed_* treats these fields as create-only
        # so the next deploy will not overwrite the correction.
        # Same pairing as the decide path, mirrored: un-reviewing the row and
        # dropping its outcome are one unit. Apart, a failure between them leaves
        # the item back in the queue while the dashboard still reports a decision
        # that no longer holds.
        try:
            with transaction.atomic():
                err = self._apply(kind, slug, language, ReviewOutcome.Outcome.NEEDS_WORK)
                if err:
                    raise _Skip(err)
                ReviewOutcome.objects.filter(
                    kind=kind, slug=slug, language=language
                ).delete()
        except _Skip as skip:
            return Response({"detail": str(skip)}, status=404)
        return Response({"ok": True, "kind": kind, "slug": slug, "language": language})


class _Skip(Exception):
    """A row the reviewer's decision cannot be applied to.

    Raised rather than returned so the surrounding ``transaction.atomic()``
    rolls back: a refusal discovered midway must not leave a half-applied
    decision behind. Carries the reason the API reports.
    """


def _tally(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        out[r[field]] = out.get(r[field], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


class AdminReviewDetailView(APIView):
    """Source and translation, split into aligned blocks, for in-place review.

    Bodies are fetched here rather than inlined into the queue payload: a
    36-chapter book is megabytes of HTML, and the queue would carry all of it to
    render a list of titles.

    Blocks are produced with the same split the translation pipeline uses —
    ``re.split(r'(<[^>]+>)', body_html)``, keeping the text runs — so the admin
    view and the translator agree on what a block is. When the two editions
    disagree on block count the response says so plainly instead of pairing by
    index anyway; a silently shifted diff is worse than no diff.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        q = request.query_params
        kind, slug, language = q.get("kind"), q.get("slug"), q.get("language")
        if kind not in AdminReviewQueueView.KINDS or not slug or not language:
            return Response({"detail": "kind, slug and language are required."}, status=400)

        if kind == "book":
            try:
                number = int(q.get("chapter") or 1)
            except (TypeError, ValueError):
                number = 1
            # Chapter's positional field is `order`, not `number`.
            src = self._chapter(slug, "en", number)
            tgt = self._chapter(slug, language, number)
            chapters = list(
                Chapter.objects.filter(book__slug=slug, book__language=language)
                .order_by("order")
                .values("order", "title")
            )
        else:
            chapters = []
            number = None
            src, tgt = AdminReviewQueueView._bodies(
                {"kind": kind, "slug": slug, "language": language}
            )
        if src is None and tgt is None:
            return Response({"detail": "Nothing to review for that item."}, status=404)

        s_blocks, t_blocks = _blocks(src or ""), _blocks(tgt or "")
        notes = list(
            TranslationNote.objects.filter(kind=kind, slug=slug, language=language).values(
                "reference", "status", "block_index", "source_file"
            )
        )
        return Response(
            {
                "kind": kind,
                "slug": slug,
                "language": language,
                "chapter": number,
                "chapters": chapters,
                "source": {"language": "en", "blocks": s_blocks},
                "target": {"language": language, "blocks": t_blocks},
                "aligned": len(s_blocks) == len(t_blocks),
                "block_counts": [len(s_blocks), len(t_blocks)],
                "notes": notes,
            }
        )

    @staticmethod
    def _chapter(slug, language, number):
        return (
            Chapter.objects.filter(book__slug=slug, book__language=language, order=number)
            .values_list("body_html", flat=True)
            .first()
        )


_BLOCK_SPLIT = re.compile(r"</(?:p|li|blockquote|h[1-6])>", re.I)


def _blocks(html: str) -> list[str]:
    """Rendered text of each block, in document order."""
    out = []
    for chunk in _BLOCK_SPLIT.split(html or ""):
        text = unescape(re.sub(r"<[^>]+>", "", chunk))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


# --- Content audit (quality + integrity) -------------------------------------
# Chapter-quality heuristics (chapter_flags + thresholds) live in library.qa,
# the single source of truth shared with the import preview.

# Per-list cap so the payload stays bounded on a large library; totals are still
# reported.
AUDIT_LIMIT = 100


def _capped(items: list) -> dict:
    return {"total": len(items), "items": items[:AUDIT_LIMIT]}


class AdminAuditView(APIView):
    """Content-quality and data-integrity audit for the admin dashboard.

    Quality checks port the ``book-qa`` skill's heuristics (generic titles,
    tiny/giant/fragmented chapters, missing drop caps, mid-sentence splits,
    duplicate titles). Integrity checks cover structural problems (empty books,
    empty chapters, chapter-order gaps, broken reading-plan day references).

    Read-only, admin-gated. One streamed pass over chapters plus a few small
    aggregate/lookup queries; heuristics are advisory — read the body before
    acting (see the skill's known-accepted list).
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        quality, per_book = self._scan_chapters()
        quality["duplicate_titles"] = self._duplicate_titles(per_book["titles"])
        integrity = {
            "empty_books": _capped(self._empty_books()),
            "empty_chapters": quality.pop("_empty_chapters"),
            "order_gaps": _capped(self._order_gaps(per_book["orders"])),
            "broken_plan_days": _capped(self._broken_plan_days()),
        }
        return Response({"quality": quality, "integrity": integrity})

    def _scan_chapters(self):
        maxima = {
            r["book_id"]: r["mx"]
            for r in Chapter.objects.values("book_id").annotate(mx=Max("order"))
        }
        generic, tiny, giant, fragmented, dropcap, mid_split, empty = (
            [], [], [], [], [], [], []
        )
        titles: dict[str, list[str]] = {}
        orders: dict[str, list[int]] = {}

        rows = Chapter.objects.select_related("book").values(
            "book_id", "book__slug", "book__language", "order", "title",
            "word_count", "body_html", "body_text",
        )
        for c in rows.iterator(chunk_size=50):
            slug = c["book__slug"]
            lang = c["book__language"]
            order = c["order"]
            title = (c["title"] or "").strip()
            wc = c["word_count"] or 0
            body = (c["body_text"] or "").strip()

            titles.setdefault(slug, []).append(title)
            orders.setdefault(slug, []).append(order)

            def finding(slug=slug, lang=lang, order=order, title=title, **extra):
                return {"book": slug, "language": lang, "order": order, "title": title, **extra}

            if not title or GENERIC_TITLE.match(title):
                generic.append(finding())
            if not body or wc == 0:
                empty.append(finding())
                continue  # remaining checks need body text
            if 0 < wc < TINY_MAX:
                tiny.append(finding(word_count=wc))
            if wc > GIANT_MIN:
                giant.append(finding(word_count=wc))

            paras = c["body_html"].count("<p")
            if paras >= FRAG_MIN_PARAS and wc >= FRAG_MIN_WORDS and wc / paras < FRAG_MAX_AVG:
                fragmented.append(finding(avg_words=round(wc / paras, 1), paragraphs=paras))

            first_alpha = next((ch for ch in body if ch.isalpha()), "")
            if first_alpha and first_alpha.islower():
                dropcap.append(finding(starts=body[:40]))

            if order < maxima.get(c["book_id"], order) and not body.endswith(TERMINAL_PUNCT):
                mid_split.append(finding(ends=body[-40:]))

        quality = {
            "generic_titles": _capped(generic),
            "tiny_chapters": _capped(tiny),
            "giant_chapters": _capped(giant),
            "fragmented": _capped(fragmented),
            "missing_dropcap": _capped(dropcap),
            "mid_sentence_splits": _capped(mid_split),
            "_empty_chapters": _capped(empty),
        }
        return quality, {"titles": titles, "orders": orders}

    def _duplicate_titles(self, titles_by_book: dict) -> dict:
        out = []
        for slug, titles in titles_by_book.items():
            seen: dict[str, int] = {}
            for t in titles:
                if t:
                    seen[t] = seen.get(t, 0) + 1
            for title, n in seen.items():
                if n > 1:
                    out.append({"book": slug, "title": title, "count": n})
        out.sort(key=lambda r: (-r["count"], r["book"]))
        return _capped(out)

    def _empty_books(self) -> list[dict]:
        books = (
            Book.objects.annotate(n=Count("chapters"))
            .filter(n=0)
            .select_related("author")
            .order_by("language", "slug")
        )
        return [
            {"book": b.slug, "language": b.language, "title": b.title, "author": b.author.name}
            for b in books
        ]

    def _order_gaps(self, orders_by_book: dict) -> list[dict]:
        out = []
        for slug, orders in orders_by_book.items():
            present = set(orders)
            expected = set(range(1, max(orders) + 1))
            missing = sorted(expected - present)
            if missing:
                out.append({"book": slug, "missing": missing, "count": len(orders)})
        out.sort(key=lambda r: r["book"])
        return out

    def _broken_plan_days(self) -> list[dict]:
        valid = set(
            Chapter.objects.values_list("book__slug", "book__language", "order")
        )
        out = []
        days = PlanDay.objects.select_related("plan").values(
            "plan__slug", "plan__language", "day", "book_slug", "chapter_order"
        )
        for d in days:
            key = (d["book_slug"], d["plan__language"], d["chapter_order"])
            if key not in valid:
                out.append(
                    {
                        "plan": d["plan__slug"],
                        "language": d["plan__language"],
                        "day": d["day"],
                        "book": d["book_slug"],
                        "order": d["chapter_order"],
                    }
                )
        out.sort(key=lambda r: (r["plan"], r["day"]))
        return out


