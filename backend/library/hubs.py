"""Biography hubs: writers grouped by tradition and by place.

A hub is a browse page of PEOPLE — "Puritan writers", "Christian writers from
Wales" — at ``/biographies/tradition/<slug>/`` or ``/biographies/place/<slug>/``.
Nothing in the schema records a writer's tradition or country, so the grouping
is curated data, kept in two kinds of file under ``data/hubs/``:

- ``members.json`` — every hub's kind, slug and member author slugs. A place
  may name the region it belongs to; a region's members are its own list plus
  the members of every place under it, so a writer tagged "Wales" is on the
  "Britain & Ireland" page without being listed twice.
- ``prose/<language>.json`` — ``{slug: {name, intro, qa}}``. There is no English
  fallback, as with topic shelves: a hub a language has no prose for does not
  exist in that language.

A hub exists in a language only when it has prose there AND at least
``MIN_MEMBERS`` of its writers are listed on that language's Biographies page
(``Author.objects.listed_in_biographies``). The floor keeps thin pages out of
the index; the listing rule means a hub never shows a writer whose card would
render blank.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "hubs"
MIN_MEMBERS = 4
KINDS = ("tradition", "region", "place")


def raw_members() -> list[dict]:
    """The hub list as written in ``members.json``."""
    return json.loads((DATA_DIR / "members.json").read_text(encoding="utf-8"))["hubs"]


def raw_prose() -> dict[str, dict[str, dict]]:
    """``{language: {slug: entry}}``, ``_note`` keys dropped.

    Uncached, like the topic loader: a dozen small files cost microseconds, and
    a cache would outlive a test that edits them.
    """
    return {
        path.stem: {
            slug: entry
            for slug, entry in json.loads(path.read_text(encoding="utf-8")).items()
            if not slug.startswith("_")
        }
        for path in sorted((DATA_DIR / "prose").glob("*.json"))
    }


def memberships(hubs: list[dict] | None = None) -> dict[str, list[str]]:
    """``{hub slug: member slugs}`` with each region's places folded in."""
    hubs = raw_members() if hubs is None else hubs
    out = {h["slug"]: list(h["members"]) for h in hubs}
    for h in hubs:
        if h["kind"] == "place" and h.get("region"):
            region = out[h["region"]]
            region.extend(m for m in h["members"] if m not in region)
    return out


def visible_slugs(language: str) -> set[str]:
    """The writers the Biographies page lists in ``language`` — one query."""
    from .models import Author

    return set(Author.objects.listed_in_biographies(language).values_list("slug", flat=True))


class Hubs:
    """The hubs as they stand in one request: data read once, and the set of
    listed writers fetched at most once per language however many hubs, fields
    or languages ask."""

    def __init__(self):
        self.hubs = raw_members()
        self.prose = raw_prose()
        self.members = memberships(self.hubs)
        self._visible: dict[str, set[str]] = {}

    def visible(self, language: str) -> set[str]:
        if language not in self._visible:
            self._visible[language] = visible_slugs(language)
        return self._visible[language]

    def listed_members(self, slug: str, language: str) -> list[str]:
        visible = self.visible(language)
        return [m for m in self.members[slug] if m in visible]

    def exists(self, slug: str, language: str) -> bool:
        return slug in self.prose.get(language, {}) and (
            len(self.listed_members(slug, language)) >= MIN_MEMBERS
        )

    def languages(self, slug: str) -> list[str]:
        """Every language this hub exists in — its hreflang set."""
        return sorted(lang for lang in self.prose if self.exists(slug, lang))

    def for_language(self, language: str) -> list[dict]:
        """The hubs that exist in ``language``, in file order, with their prose."""
        out = []
        for h in self.hubs:
            if not self.exists(h["slug"], language):
                continue
            prose = self.prose[language][h["slug"]]
            out.append(
                {
                    "kind": h["kind"],
                    "slug": h["slug"],
                    "region": h.get("region") or None,
                    "name": prose["name"],
                    "intro": prose["intro"],
                    "qa": prose.get("qa", []),
                    "members": self.listed_members(h["slug"], language),
                    "available_languages": self.languages(h["slug"]),
                }
            )
        return out

    def for_author(self, author_slug: str, language: str) -> list[dict]:
        """The hubs an author page links to: each tradition they belong to, and
        the most specific place that exists in ``language`` — their country's
        page, else its region's (a Canadian writer links to North America when
        Canada has too few writers for a page of its own)."""
        if author_slug not in self.visible(language):
            return []
        chips = []
        places = []
        for h in self.hubs:
            if author_slug not in self.members[h["slug"]] or not self.exists(h["slug"], language):
                continue
            chip = {"kind": h["kind"], "slug": h["slug"], "name": self.prose[language][h["slug"]]["name"]}
            (chips if h["kind"] == "tradition" else places).append((h, chip))
        # A place outranks its region; a region stands only when none of its
        # places carries this writer here.
        placed_regions = {h.get("region") for h, _ in places if h["kind"] == "place"}
        best = [c for h, c in places if h["kind"] == "place" or h["slug"] not in placed_regions]
        return [c for _, c in chips] + best
