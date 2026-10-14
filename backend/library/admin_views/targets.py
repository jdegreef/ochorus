"""Progress against the Language Content Targets (``library.content_targets``).

Two readers share one rule for what counts as *done*: the language page's
"Level 1 targets" panel (every item, with its state) and the Language health
scoreboard (one count per language). An item is done when this language has a
**published** edition of it. For a biography that means a translated
``bio_html``, and for a topic shelf a translated title. A drafted but
unpublished edition is reported as such, but it is not done.
"""

from __future__ import annotations

from collections import defaultdict

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..content_targets import LEVEL_1, Level
from ..models import (
    Article,
    Author,
    AuthorTranslation,
    Book,
    Plan,
    Sermon,
    Topic,
    TopicTranslation,
)
from ..plan_seed import CURATED_PLANS, LAUNCH_PLANS, plan_sources
from .jobs import translation_blocked

# kind → (translation-job type, label). Order is the panel's order.
KIND_META = {
    "bios": ("bio", "Biographies"),
    "books": ("book", "Books"),
    "sermons": ("sermon", "Sermons"),
    "plans": ("plan", "Reading plans"),
    "articles": ("article", "Articles"),
}

_WORK_MODELS = {"books": Book, "sermons": Sermon, "articles": Article, "plans": Plan}


def _editions(level: Level, codes: list[str]) -> dict[str, dict[str, dict[str, dict]]]:
    """kind → code → slug → {published, reviewed} for every edition of a level
    item in ``codes``. One query per kind, whatever the number of languages."""
    out: dict[str, dict[str, dict[str, dict]]] = {k: defaultdict(dict) for k in KIND_META}
    for kind, model in _WORK_MODELS.items():
        fields = ["language", "slug", "is_published"] + (["source_type"] if kind != "plans" else [])
        for r in model.objects.filter(slug__in=level.slugs(kind), language__in=codes).values(*fields):
            # A plan has no review state of its own: it is as reviewed as its text.
            reviewed = r.get("source_type") != Book.SourceType.AI_UNREVIEWED
            out[kind][r["language"]][r["slug"]] = {"published": r["is_published"], "reviewed": reviewed}
    bios = (
        AuthorTranslation.objects.filter(author__slug__in=level.slugs("bios"), language__in=codes)
        .exclude(bio_html="")
        .values("language", "author__slug", "reviewed")
    )
    for r in bios:
        out["bios"][r["language"]][r["author__slug"]] = {"published": True, "reviewed": r["reviewed"]}
    return out


def _topic_counts(codes: list[str]) -> tuple[int, dict[str, int]]:
    """(published shelves, code → shelves with a title in that language)."""
    topics = Topic.objects.filter(is_published=True)
    counts: dict[str, int] = defaultdict(int)
    for code in (
        TopicTranslation.objects.filter(topic__in=topics, language__in=codes)
        .exclude(title="")
        .values_list("language", flat=True)
    ):
        counts[code] += 1
    return topics.count(), counts


def level_summary(level: Level, codes: list[str]) -> dict[str, dict]:
    """code → {done, total} across every kind plus topics, for the scoreboard."""
    editions = _editions(level, codes)
    n_topics, topics = _topic_counts(codes)
    total = sum(len(level.slugs(k)) for k in KIND_META) + (n_topics if level.all_topics else 0)
    out = {}
    for code in codes:
        done = sum(
            sum(1 for e in editions[k][code].values() if e["published"]) for k in KIND_META
        ) + (topics[code] if level.all_topics else 0)
        out[code] = {"done": done, "total": total}
    return out


def _titles(level: Level) -> dict[str, dict[str, tuple[str, str]]]:
    """kind → slug → (title, author) from the English editions."""
    out: dict[str, dict[str, tuple[str, str]]] = {}
    for kind in ("books", "sermons"):
        rows = _WORK_MODELS[kind].objects.filter(language="en", slug__in=level.slugs(kind))
        out[kind] = {
            r["slug"]: (r["title"], r["author__name"] or "") for r in rows.values("slug", "title", "author__name")
        }
    # Articles, plans and authors carry no byline worth showing here.
    for kind, qs, field in (
        ("articles", Article.objects.filter(language="en"), "h1"),
        ("plans", Plan.objects.filter(language="en"), "title"),
        ("bios", Author.objects.all(), "name"),
    ):
        rows = qs.filter(slug__in=level.slugs(kind)).values_list("slug", field)
        out[kind] = {slug: (title, "") for slug, title in rows}
    return out


def _plan_needs() -> dict[str, tuple[list[str], list[str]]]:
    needs = {p[0]: ([p[1]], []) for p in LAUNCH_PLANS}
    needs.update({p[0]: plan_sources(p[3]) for p in CURATED_PLANS})
    return needs


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageTargetsView(APIView):
    """``GET /api/admin/languages/<code>/targets/``: this language against the
    Level 1 content targets, every item with its state. A missing plan also
    names the source books and articles it is waiting on, since a plan can't be
    built here until they exist."""

    def get(self, request, code):
        code = code.lower()
        level = LEVEL_1
        editions = _editions(level, [code])
        titles = _titles(level)
        needs = _plan_needs()
        kinds = []
        for kind, (job_type, label) in KIND_META.items():
            have = editions[kind][code]
            # Plans are one flat list; every other kind is grouped.
            groups = (("", level.plans),) if kind == "plans" else getattr(level, kind)
            out_groups = []
            for group_label, slugs in groups:
                items = []
                for slug in slugs:
                    edition = have.get(slug)
                    title, author = titles[kind].get(slug, (slug, ""))
                    item = {
                        "slug": slug,
                        "title": title,
                        "author": author,
                        "done": bool(edition and edition["published"]),
                        "drafted": bool(edition and not edition["published"]),
                        "reviewed": bool(edition and edition["reviewed"]),
                        "blocked": translation_blocked(job_type, slug),
                    }
                    if kind == "plans" and not item["done"]:
                        need_books, need_articles = needs.get(slug, ([], []))
                        item["waiting_on"] = [
                            s for s in need_books if not editions["books"][code].get(s, {}).get("published")
                        ] + [s for s in need_articles if not editions["articles"][code].get(s, {}).get("published")]
                    items.append(item)
                out_groups.append({"label": group_label, "items": items})
            flat = [i for g in out_groups for i in g["items"]]
            kinds.append(
                {
                    "key": kind,
                    "job_type": job_type,
                    "label": label,
                    "target": len(flat),
                    "done": sum(i["done"] for i in flat),
                    "reviewed": sum(i["done"] and i["reviewed"] for i in flat),
                    "groups": out_groups,
                }
            )
        n_topics, topics = _topic_counts([code])
        return Response(
            {
                "language": code,
                "level": {"number": level.number, "name": level.name},
                "kinds": kinds,
                "topics": {"target": n_topics, "done": topics[code]} if level.all_topics else None,
            }
        )
