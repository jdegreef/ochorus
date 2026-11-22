"""Full-text search across the library.

The one place the search query lives. Two kinds of hit come back:

* **Entities** — a book, author, topic or plan *itself* (a navigational match):
  "take me to that page". Ranked above body matches so typing a title or an
  author's name leads with the thing you meant.
* **Passages** — a chapter or sermon whose body text matches (a content match),
  with the matched words wrapped in ``HL_START`` / ``HL_END`` markers.

On Postgres (production): websearch-style parsing, weighted ranking via
``SearchRank`` and ``SearchHeadline`` snippets. On SQLite (dev): a
case-insensitive substring fallback producing the same response shape. Snippets
are plain text either way; the client escapes them and renders the markers as
``<mark>``.
"""

from __future__ import annotations

import difflib
import re
from contextlib import contextmanager, nullcontext

from django.db import connection, transaction
from django.db.models import (
    Case,
    Exists,
    F,
    FloatField,
    Func,
    OuterRef,
    Q,
    Subquery,
    TextField,
    Value,
    When,
)
from django.db.models.functions import Coalesce

# Config lookup shared with the stored-vector write path (library/fts.py) so
# query config always matches what the row was indexed with.
from .cover_face import cover_face
from .fts import (
    PREFIX_LANGUAGES,
    STORED_KINDS,
    SUBSTRING_LANGUAGES,
    config_for,
    positive_words,
    query_tokens,
    search_query,
    uses_fts,
)
from .http_cache import MAX_AGE
from .models import (
    Article,
    Author,
    Book,
    Chapter,
    ChapterCitation,
    Plan,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from .people import People, fold, strongest
from .people import words as name_words
from .scripture import quoted_reference, reference_verse_ids
from .search_aliases import books_named, other_names
from .search_answers import ANSWER_CAP, answer_hits
from .search_quotes import QUOTE_CAP, quote_hits

MAX_RESULTS = 30

# Shorter than this is a keystroke, not a query. Two rather than three because a
# 2-character query is a real search in e.g. Chinese; every caller that asks the
# engine for anything applies it, so it lives here rather than at each entry.
MIN_QUERY_LEN = 2


def min_query_len(language: str) -> int:
    """The shortest query worth running: one character in a SUBSTRING_LANGUAGE,
    where a single kanji (神, 愛, 罪, 主) is a whole word."""
    return 1 if language in SUBSTRING_LANGUAGES else MIN_QUERY_LEN

# Navigational (entity) matches lead over body-text matches: a book/author/topic
# whose title *is* the query is almost always what the reader wants.
ENTITY_BOOST = 1.6

# A young-reader edition (`<base>-teens`, `<base>-children`: CLAUDE.md) is a
# retelling of a classic, written short and plain, so it out-ranked the full
# text for that classic's own title: "grace" listed All of Grace (For Teens)
# above All of Grace (bug review 2026-11-22, #43). Its rank is damped unless the
# query asks for young readers itself.
YOUNG_EDITION_SUFFIXES = ("-teens", "-children")
YOUNG_EDITION_DAMP = 0.75
YOUNG_READER_WORDS = re.compile(
    r"\b(teens?|teenagers?|youth|young|kids?|child(ren)?|children's)\b", re.I
)


def _book_rank(rank, ctx):
    """A book's rank, with a young-reader edition damped unless the query is
    looking for one. Applied in SQL, so the merged list's cap, the Books tab's
    page and its order all agree."""
    from django.db.models import Case, FloatField, Q, Value, When

    if YOUNG_READER_WORDS.search(ctx.q):
        return rank
    young = Q()
    for suffix in YOUNG_EDITION_SUFFIXES:
        young |= Q(slug__endswith=suffix)
    return rank * Case(
        When(young, then=Value(YOUNG_EDITION_DAMP)),
        default=Value(1.0),
        output_field=FloatField(),
    )


def _ranked_expr(kind, rank, ctx):
    """The rank a row of `kind` sorts by (`_book_rank` for books)."""
    return _book_rank(rank, ctx) if kind == "book" else rank


# Per-type caps so one kind can't crowd the others out of the merged list. This
# is the set of QUERYSET-backed types; "scripture" is deliberately absent — it is
# a synthesized, reference-triggered hit with no queryset, handled out of band in
# page_by_type and led directly in search_library (see _scripture_page_hits).
CAPS = {
    "author": 5,
    "book": 8,
    "topic": 5,
    "plan": 5,
    "article": 5,
    "chapter": 20,
    "sermon": 6,
}

# How many matches of one type a "show more" page returns.
PAGE_SIZE = 20

# Counting is bounded, and the number the reader sees says so ("200+"). An exact
# count of every chapter matching "prayer" is a scan of the whole corpus on every
# keystroke, and nobody needs the difference between 340 and 200+ — they need to
# know the list in front of them is a sample rather than the library, which is
# exactly what the capped page could not tell them.
COUNT_CEILING = 200

HL_START = "⟦"
HL_END = "⟧"

# The span of a passage a snippet is cut from (see _Snippet): characters
# kept before the match point, and in all. A headline is at most forty words,
# about 250 characters; the rest is room for ts_headline to choose a denser
# passage than the first one. Measured on the fixture, 2,400 cost no more than
# 1,200 and left fewer snippets differing from the whole-body choice.
SNIPPET_BEFORE = 800
SNIPPET_WINDOW = 2400

# How long a memoised answer may outlive a change ContentRevision can't see —
# an edit in the Django admin, which bumps nothing. The public API's own
# freshness promise (http_cache.MAX_AGE: an admin's change reaches readers in
# about a minute), so a takedown is no slower to leave search than any page.
MEMO_SECONDS = MAX_AGE


def memoized(name: str, compute, *key):
    """``compute()``, remembered per worker until content changes.

    Search answers are a pure function of the query and the content, and the
    same few queries are most of the traffic — so the second reader to type
    "prayer" shouldn't pay for the first one's index scans. ``key`` is whatever
    the answer depends on beyond the content revision.
    """
    from .invalidation import revision_cached

    return revision_cached("search", f"search:{name}", compute, *key, timeout=MEMO_SECONDS)


_SPACE = re.compile(r"\s")
#: Scripts written without spaces (kana, kanji, full-width forms): a snippet may
#: start mid-run there, since there is no word boundary to back off to.
_UNSPACED = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")


def to_word_end(text: str, end: int, floor: int) -> str:
    """``text[:end]`` backed off to the last whole word (never below ``floor``),
    without a trailing ",;:" or space before the "…" that follows it."""
    if end < len(text) and not text[end].isspace():
        cut = max((m.start() for m in _SPACE.finditer(text, floor, end)), default=-1)
        if cut >= floor and cut > 0:
            end = cut
    return text[:end].rstrip().rstrip(",;:").rstrip()


def fallback_snippet(text: str, query: str, radius: int = 90) -> str:
    """Excerpt centred on the first match, with all matches marker-wrapped.

    Used on SQLite (dev), and for entity snippets everywhere (a book/author's
    own prose is short enough not to need SearchHeadline). Returns "" for empty
    text, and the head of the text when the query isn't found in it.
    """
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        if len(text) <= radius * 2:
            return text
        return to_word_end(text, radius * 2, 0) + "…"
    start = max(0, idx - radius)
    end = min(len(text), idx + len(query) + radius)
    # Cut on word boundaries: "…erywhere who desire" reads as a typo.
    if start > 0 and not text[start - 1].isspace():
        space = _SPACE.search(text, start, idx)
        if space:
            start = space.end()
        elif not _UNSPACED.match(text, start):
            start = idx
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    excerpt = to_word_end(text, end, idx + len(query))[start:] if suffix else text[start:end]
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    excerpt = pattern.sub(lambda m: f"{HL_START}{m.group(0)}{HL_END}", excerpt)
    return f"{prefix}{excerpt}{suffix}"


#: The places a search can be narrowed to. Each names a shelf the reader is
#: already standing in — an author, a topic, or the book open in front of them.
SCOPES = ("author", "topic", "book")


def parse_scope(raw: str) -> tuple[str, str] | None:
    """``"author:andrew-murray"`` → ``("author", "andrew-murray")``.

    Returns None for anything malformed, which searches the whole library. A
    scope naming a place that doesn't EXIST is a different matter and is left to
    the filters: they find nothing, which is the honest answer.
    """
    kind, _, slug = (raw or "").strip().lower().partition(":")
    if kind in SCOPES and slug:
        return kind, slug
    return None


#: How each scope kind names itself, given its row.
_SCOPE_LABEL = {
    "author": lambda row, language: row.name,
    "topic": lambda row, language: row.title_for(language),
    "book": lambda row, language: row.title,
}


def scope_entry(scope: tuple[str, str], language: str) -> dict | None:
    """The scope as the reader sees it — ``{kind, slug, label}`` — or None.

    Resolved here so the page can name the shelf it is searching without a second
    request, and so a scope naming something that doesn't exist *in this
    language* comes back as None rather than as a chip labelling a place the
    reader can't reach. (There is no English fallback: a topic with no title in
    Swahili is not a Swahili shelf.)

    "Exists in this language" is asked of ``_base_querysets`` rather than
    restated, so the chip can never name a shelf the search then finds nothing
    in — the two answers come from the same filter.
    """
    kind, slug = scope
    row = _base_querysets(language)[kind].filter(slug=slug).first()
    label = _SCOPE_LABEL[kind](row, language) if row else None
    return {"kind": kind, "slug": slug, "label": label} if label else None


def _scoped(qs: dict, scope: tuple[str, str]) -> dict:
    """Narrow every type to what lives inside one author / topic / book.

    Only the things that can be *inside* a place take part: works and their
    passages. Authors, topics and plans are ways in to a scope rather than
    contents of one — searching within Andrew Murray and being shown Andrew
    Murray is noise — so they match nothing and their chips simply don't appear.
    Same for the scoped book itself: you are already in it.
    """
    kind, slug = scope
    empty = {k: v.none() for k, v in qs.items()}
    if kind == "author":
        return {
            **empty,
            "book": qs["book"].filter(author__slug=slug),
            "chapter": qs["chapter"].filter(book__author__slug=slug),
            "sermon": qs["sermon"].filter(author__slug=slug),
        }
    if kind == "topic":
        # Topic membership is by slug (see TopicBook) so it holds across
        # languages — the scope means the same shelf whatever you're reading in.
        # is_published on the topic as well as the works: an unpublished shelf
        # narrows to published books, so nothing unreleased is returned — but
        # diffing a scoped result set against an unscoped one would still read
        # off a draft shelf's curation.
        members = {"topic__slug": slug, "topic__is_published": True}
        books = TopicBook.objects.filter(**members).values("book_slug")
        sermons = TopicSermon.objects.filter(**members).values("sermon_slug")
        return {
            **empty,
            "book": qs["book"].filter(slug__in=books),
            "chapter": qs["chapter"].filter(book__slug__in=books),
            "sermon": qs["sermon"].filter(slug__in=sermons),
        }
    if kind == "book":
        return {**empty, "chapter": qs["chapter"].filter(book__slug=slug)}
    # A kind in SCOPES with no branch here would otherwise fall through to
    # whichever narrowing happened to be last — searching nothing is the safe
    # failure, and parse_scope already rejects kinds this doesn't know.
    return empty


def _base_querysets(language: str, scope: tuple[str, str] | None = None) -> dict:
    """What is eligible to match, per type, in one place.

    Extracted because three things need it now — the merged search, the per-type
    counts and the per-type pages — and a count computed from a different filter
    than the results is worse than no count at all. ``scope`` narrows all three
    together for the same reason.
    """
    # No hit reads body_html or a vector (the queries name the vectors in SQL
    # without loading them), so those stay in the database. body_text stays
    # loaded for the SQLite and "show more" snippets, built in Python.
    chapters = (
        Chapter.objects.filter(book__is_published=True, book__language=language)
        .select_related("book", "book__author")
        .defer("body_html", "search_vector", "book__search_vector")
    )
    sermons = (
        Sermon.objects.filter(is_published=True, language=language)
        .select_related("author")
        .defer("body_html", "search_vector")
    )
    books = Book.objects.filter(is_published=True, language=language).select_related(
        "author"
    )
    plans = Plan.objects.filter(is_published=True, language=language)
    # Articles are the site's own SEO hubs — per-language rows with NO English
    # fallback (like books and plans), so filtering to this language is the
    # whole of the gating: English is the only language with rows today, so an
    # article hit can only surface for an English query, and a future translation
    # ungates itself the moment its row exists. Nothing here is inside a scope
    # (an article has no author/topic/book to live under), so _scoped drops it.
    # defer the two big unused columns: search reads only the titling fields
    # (h1/meta_title/description for the vector, h1/description/slug/date for the
    # hit), so pulling each matched article's full body_html and `related` JSON
    # across the wire per keystroke is pure waste — the other entities have no
    # such blob to pay for.
    articles = Article.objects.filter(is_published=True, language=language).defer(
        "body_html", "related"
    )
    topics = Topic.objects.filter(is_published=True).prefetch_related("translations")
    if language != "en":
        # A shelf with no title in this language doesn't exist here (see
        # TopicListView), so it must not surface as a titleless search hit.
        # Exists() rather than a join filter: a topic translated into Spanish
        # but not Swahili must not qualify for Swahili on a sibling row.
        topics = topics.filter(
            Exists(
                TopicTranslation.objects.filter(
                    topic=OuterRef("pk"), language=language
                ).exclude(title="")
            )
        )
    # Only authors who actually have something published to read in this language,
    # mirroring the biographies roster (no ghost authors from unpublished drafts).
    # Imprints are excluded as the roster excludes them: a house byline is not a
    # person, and its books are still found as books (its shelf is /originals).
    # Exists() rather than a join + DISTINCT: the join fanned each author out to
    # one row per book and sermon (~1,600 rows for 148 authors), and DISTINCT
    # then sorted on every column — the query-time vector included, so each
    # bio was re-tokenised once per work. That was half a second per keystroke.
    published = {"author": OuterRef("pk"), "is_published": True, "language": language}
    authors = (
        Author.objects.filter(is_imprint=False)
        .filter(
            Exists(Book.objects.filter(**published))
            | Exists(Sermon.objects.filter(**published))
        )
        .prefetch_related("translations")
    )
    out = {
        "author": authors,
        "book": books,
        "topic": topics,
        "plan": plans,
        "article": articles,
        "chapter": chapters,
        "sermon": sermons,
    }
    return _scoped(out, scope) if scope else out


#: The kinds whose vectors are big enough to be TOASTed — see _index_scans.
TOASTED = frozenset({"chapter", "sermon"})


@contextmanager
def _index_scans(language: str):
    """Steer Postgres off sequential scans for the TOASTED kinds' queries inside.

    library_chapter's heap is ~20 MB and its vectors ~750 MB beside it, and the
    planner prices a sequential scan by the heap alone. So for any common word
    it chose to scan every chapter in every language — detoasting each vector
    to test it — over the GIN index that answers the same match in a few
    milliseconds (measured on the fixture: "prayer" 560 ms -> 49 ms ranked,
    615 ms -> 12 ms counted).

    Only for those tables. Elsewhere a sequential scan is often the right plan:
    the entity vectors are small, and authors and topics have no vector index
    at all — with sequential scans penalised the planner walked them through
    other indexes instead, measured ten times slower.

    SET LOCAL needs a transaction, so this opens one; it is also what keeps the
    setting from leaking to the next request on a pooled connection. If the
    body raises, rolling the atomic block back reverts the setting with it.
    """
    if not uses_fts(language):  # SQLite, or a substring search: no vectors read
        yield
        return
    # Inside a caller's transaction (a test, an atomic view) SET LOCAL lasts
    # until the OUTERMOST one ends, so it must be put back; otherwise COMMIT does.
    nested = connection.in_atomic_block
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting('enable_seqscan'),"
            " set_config('enable_seqscan', 'off', true)"
        )
        previous = cursor.fetchone()[0]
        yield
        if nested:
            cursor.execute("SELECT set_config('enable_seqscan', %s, true)", [previous])


def search_library(q: str, language: str, scope=None) -> list[dict]:
    """Ranked search hits for ``q`` in ``language``.

    Entities (books, authors, topics, plans, articles) plus passages (chapters,
    sermons), merged and capped at ``MAX_RESULTS``. ``scope`` narrows the search
    to one author / topic / book — see ``_scoped``.
    """
    qs = _base_querysets(language, scope)
    # Only the two kinds the scripture-reference pass below still needs by name;
    # the per-type search itself now takes the whole dict (like count_by_type).
    chapters, sermons = qs["chapter"], qs["sermon"]

    ctx = _Ctx(q=q, language=language)
    if uses_fts(language):
        base = _search_postgres(ctx, qs)
    else:
        base = _search_fallback(ctx, qs)

    # If the query is itself a scripture reference, lead with everything that
    # engages the passage — sermons preached on an overlapping text, then
    # chapters whose body CITES an overlapping reference (ChapterCitation
    # verse-id spans). Matched by verse id, so it works where plain text
    # search can't (abbreviations, chapter-only, a verse inside a range).
    # The scripture PAGE itself leads: a reference query's most direct answer is
    # the hub that gathers everything treating the passage, above the individual
    # sermons and chapters that do. English-only and never inside a scope (it is
    # a global hub, not something that lives under an author/book).
    # A verse quoted by its words ("for god so loved the world") is read as
    # its reference, so it draws the same hub, sermons and citing chapters.
    ref = verse_quoted(q, language) or q
    extra = _scripture_page_hits(ref, language, scope)
    extra += _scripture_sermon_hits(ref, sermons, base)
    cite_hits = _scripture_chapter_hits(ref, chapters)
    if cite_hits:
        # A chapter found by BOTH citation and plain text keeps its citation
        # hit (ranked by specificity, snippet centred on the reference) and
        # drops the text duplicate from the base list.
        cited = {(h["book_slug"], h["chapter_order"]) for h in cite_hits}
        base = [
            h
            for h in base
            if h["type"] != "chapter"
            or (h["book_slug"], h["chapter_order"]) not in cited
        ]
    extra += cite_hits
    merged = (extra + base)[:MAX_RESULTS] if extra else base
    # Quotations ride beside the capped list rather than inside it: they are
    # their own section, and a few of them should never cost a passage its place.
    merged += quote_hits(q, language, ctx.writer, scope)[:QUOTE_CAP]
    # And the library's own answers, when the query asks a question.
    merged += answer_hits(q, language, scope)[:ANSWER_CAP]
    # Readers' choices last, over the finished list: they reorder what matched,
    # never add to it. Not inside a scope, where clicks aren't recorded.
    return merged if scope else apply_choices(merged, q, language)


def verse_quoted(q: str, language: str) -> str | None:
    """The verse ``q`` quotes by its words, as a reference, or None. English:
    the indexed Bibles are the English OWB and the ASV (bible_store.SEARCHABLE)."""
    return quoted_reference(q) if language == "en" else None


# --- Readers' choices ------------------------------------------------------------
# The click log (SearchClickLog) says which result readers actually opened for a
# query. A result opened again and again for the same words is the answer to
# them, whatever the text ranking thought — so it rises to the top of its kind,
# and one opened by most readers who opened anything leads the page.

#: How far back clicks count: long enough to gather a few for a steady query,
#: short enough that a change in the library (a new edition) shows within weeks.
CHOICE_DAYS = 90
#: Opens before a result moves at all. Several, so one reader (or one script —
#: the click endpoint is public, if throttled) can't reorder a query alone.
CHOICE_MIN_CLICKS = 3
#: Opens, and share of all opens for the query, before a result leads the page.
CHOSEN_MIN_CLICKS = 5
CHOSEN_SHARE = 0.5


def hit_row_key(hit: dict) -> str:
    """A hit's key as the search page keys its rows (searchResults.ts toRow)."""
    kind = hit.get("type", "")
    if kind == "chapter":
        return f"chapter:{hit.get('book_slug', '')}:{hit.get('chapter_order', '')}"
    if kind == "scripture":
        verse = hit.get("verse")
        return f"scripture:{hit.get('book_slug', '')}:{hit.get('chapter', '')}:{'' if verse is None else verse}"
    if kind == "quote":
        return f"quote:{hit.get('quote_slug', '')}"
    if kind == "answer":
        return f"answer:{hit.get('work_kind', '')}-{hit.get('work_slug', '')}"
    spec = HIT_WORK.get(kind)
    return f"{kind}:{hit.get(spec[1], '')}" if spec else ""


def click_choices(q: str, language: str) -> dict[str, int]:
    """Opens per result key for this query in the last CHOICE_DAYS days."""
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    from .models import SearchClickLog

    def compute():
        since = timezone.now() - timedelta(days=CHOICE_DAYS)
        rows = (
            SearchClickLog.objects.filter(
                language=language, query__iexact=" ".join(q.split()), created_at__gte=since
            )
            .exclude(result_key="")
            .values("result_key")
            .annotate(n=Count("id"))
        )
        return {r["result_key"]: r["n"] for r in rows}

    return memoized("choices", compute, " ".join(q.lower().split()), language)


def apply_choices(hits: list[dict], q: str, language: str) -> list[dict]:
    """``hits`` with readers' choices lifted: a result opened at least
    CHOICE_MIN_CLICKS times rises, most-opened first, ahead of the rest of its
    kind; one with CHOSEN_MIN_CLICKS opens and CHOSEN_SHARE of all of them is
    marked ``chosen`` (the page leads with it). Order is otherwise unchanged."""
    choices = click_choices(q, language)
    if not choices:
        return hits
    total = sum(choices.values())

    def opens(hit):
        n = choices.get(hit_row_key(hit), 0)
        return n if n >= CHOICE_MIN_CLICKS else 0

    lifted = sorted(hits, key=lambda h: -opens(h))  # stable: ties keep text order
    for hit in lifted:
        n = opens(hit)
        if n >= CHOSEN_MIN_CLICKS and n >= CHOSEN_SHARE * total:
            lifted = [hit, *[h for h in lifted if h is not hit]]
            hit = {**hit, "chosen": True}
            lifted[0] = hit
            break
    return lifted


class _Ctx:
    """Small carrier so the per-type builders stay readable.

    Also where the query is read as a person's name (library/people.py), once
    per search: ``people`` is who it names, strongest first, and ``person`` the
    one it names unambiguously enough to search that person's works by.
    """

    def __init__(self, q: str, language: str):
        self.q = q
        self.language = language
        self._people = None
        self._books = None
        self._corrected = None

    def _read_people(self):
        if self._people is None:
            people = People(_author_names(self.language))
            matches = people.match(self.q)
            person = strongest(matches)
            # Who counts as found by name: anyone the query is wholly the name
            # of ("john", "d l moody"), plus the one person a longer query
            # names ("d l moody prayer"). Not everyone who merely shares a
            # word with it — "gospel of john" is not a search for every John.
            found = [m for m in matches if m.whole or m is person]
            self._people = (found, people.rewrite(self.q, matches), person, matches)
        return self._people

    @property
    def people(self) -> list:
        """The authors found by name (PersonMatch), strongest first."""
        return self._read_people()[0]

    @property
    def rewritten(self) -> str | None:
        """The query with its person spelt the library's way, if that differs."""
        return self._read_people()[1]

    @property
    def corrected(self) -> str | None:
        """The query with its typos corrected (``correction``), if any."""
        if self._corrected is None:
            self._corrected = correction(self.q, self.language) or ""
        return self._corrected or None

    @property
    def aliased_books(self) -> list[tuple[str, str]]:
        """Books the query names by another title: (slug, title)."""
        if self._books is None:
            self._books = _aliased_books(self)
        return self._books

    @property
    def person(self):
        """The one person the query names by two or more words, or None."""
        return self._read_people()[2]

    @property
    def writer(self):
        """Whose words the query asks for: ``person``, or failing that the one
        writer it names by surname ("spurgeon prayer"). For quotes, where a
        surname is never what a sentence says, so one word is enough."""
        if self.person is not None:
            return self.person
        by_surname = [m for m in self._read_people()[3] if m.by_surname]
        if len(by_surname) == 1 or (
            len(by_surname) > 1 and by_surname[0].score > by_surname[1].score
        ):
            return by_surname[0]
        return None


def _author_names(language: str) -> list[tuple[int, str]]:
    """(pk, name) of every author findable in ``language`` — the whole library,
    never a scope, so "d l moody" reads the same inside a shelf as outside."""
    def compute():
        rows = list(_base_querysets(language)["author"].values_list("pk", "name", "slug"))
        names = [(pk, name) for pk, name, _ in rows]
        # And the other names each is known by, and how each language writes
        # it (library/search_aliases.py).
        names += [
            (pk, other, name)
            for pk, name, slug in rows
            for other in other_names(slug)
        ]
        return names

    return memoized("people", compute, language)


def _aliased_books(ctx) -> list[tuple[str, str]]:
    """(slug, title in this language) of the books the query names by another
    title ("de civitate dei" → The City of God), from library/search_aliases.py."""
    slugs = books_named(name_words(ctx.q))
    if not slugs:
        return []
    return list(
        Book.objects.filter(slug__in=slugs, language=ctx.language, is_published=True)
        .values_list("slug", "title")
    )


#: A name match's weight in the merged list. One the query unmistakably IS
#: ("d l moody") leads everything; a looser one ("moody", "john") is lifted
#: within its type by its strength, without outranking a strong text match.
NAMED_SCORE = 100.0
NAME_WEIGHT = 0.1


def _name_score(match) -> float:
    if match is None:
        return 0.0
    return NAMED_SCORE + match.score if match.named else NAME_WEIGHT * match.score


def _name_order(ctx):
    """An author's name-match strength, as an annotation to order pages by."""
    whens = [When(pk=m.pk, then=Value(_name_score(m))) for m in ctx.people]
    return Case(*whens, default=Value(0.0), output_field=FloatField())


#: The field naming a work's author, for the types a person's name finds.
_AUTHOR_FIELD = {"book": "author", "chapter": "book__author", "sermon": "author"}


def _query(ctx):
    """The SearchQuery for ``ctx``: the query as typed, OR'd with its person
    spelt the library's way ("d l moody" also asks for "dwight l moody"), and
    with the title of any book it names by another one ("de civitate dei" also
    asks for the phrase "The City of God")."""
    query = search_query(ctx.q, ctx.language)
    if ctx.rewritten:
        query = query | search_query(ctx.rewritten, ctx.language)
    if ctx.corrected:
        query = query | search_query(ctx.corrected, ctx.language)
    for _, title in ctx.aliased_books:
        query = query | search_query('"' + title.replace('"', " ") + '"', ctx.language)
    return query


# --- Postgres -----------------------------------------------------------------


class _Snippet(Func):
    """A passage's highlighted snippet: ts_headline over a window, not the body.

    ts_headline's cost is parsing its whole input, and a chapter runs to tens of
    thousands of characters: twenty of them were ~120 ms of every search, for a
    snippet of forty words. So it parses SNIPPET_WINDOW characters around the
    point where every query word has first appeared — the latest of their first
    occurrences, since any passage satisfying the whole query ends at or after
    it — and the whole body only where that window can't serve:

    * no point: no query word occurs literally (the row matched through its
      title or author, or a word's form is neither the typed word nor its stem);
    * or the window doesn't itself satisfy the query (``@@``): the words met
      once, apart, and the passage the query wants lies elsewhere.

    The second test is the query's own, so it knows OR, exclusions, phrases and
    Korean prefixes; a snippet is never cut from text the query doesn't match.

    A word is looked for as its stem AND as typed, at a word start: "running"
    finds "runs" through "run", while "holy" (stem "holi") is found as typed.
    The window is trimmed to whole words at both edges.
    One scalar subquery per row, so the point is found once; Postgres postpones
    it past the ORDER BY ... LIMIT, so only the capped rows pay for it.
    """

    output_field = TextField()

    #: Where a word first starts in ``body``, as 1-based char position, else NULL.
    #: regexp_instr from Postgres 15; before it, the length of what precedes it.
    _AT = {
        True: "NULLIF(regexp_instr({body}, '\\m' || {word}, 1, 1, 0, 'i'), 0)",
        False: "length(substring(lower({body}) from '^(.*?)\\m' || {word})) + 1",
    }

    def __init__(self, body, query, config: str, words: list[str]):
        super().__init__(body, query)
        self.config, self.words = config, words

    def as_sql(self, compiler, connection, **extra):
        (body, body_p), (query, query_p) = (
            compiler.compile(e) for e in self.get_source_expressions()
        )
        # Lexemes may hold regex metacharacters (to_tsvector keeps "e.g", "c++").
        word = r"regexp_replace(word, '([.^$*+?()\[\]{}|\\])', '\\\1', 'g')"
        at = self._AT[connection.pg_version >= 150000].format(body=body, word=word)
        options = f"StartSel={HL_START}, StopSel={HL_END}, MaxWords=40, MinWords=20"
        before, width = SNIPPET_BEFORE, SNIPPET_WINDOW
        sql = (
            f"(SELECT CASE WHEN to_tsvector(%s::regconfig, w.text) @@ {query}"
            f" THEN ts_headline(%s::regconfig, w.text, {query}, %s)"
            f" ELSE ts_headline(%s::regconfig, {body}, {query}, %s) END"
            # The point: each typed word's EARLIEST form (stem or as typed),
            # then the latest of those — a late "holiness" must not move the
            # window past an early "holy".
            f" FROM (SELECT max(first) AS at FROM ("
            f"   SELECT min({at}) AS first FROM unnest(%s::text[]) AS typed(given),"
            "   LATERAL (SELECT unnest(tsvector_to_array(to_tsvector(%s::regconfig, typed.given)))"
            "            UNION SELECT lower(typed.given)) AS forms(word)"
            "   GROUP BY typed.given) AS per_word) AS m,"
            f" LATERAL (SELECT greatest(1, m.at - {before}) AS start,"
            f"          substr({body}, greatest(1, m.at - {before}), {width}) AS raw) AS r,"
            # Whole words only: a cut word at either edge would show as a
            # fragment ("ndlord came"), or as a false match ("faith" of
            # "faithfulness") that the @@ test would believe.
            " LATERAL (SELECT CASE WHEN length(r.raw) < "
            f"{width} THEN t.text ELSE regexp_replace(t.text, '\\s+\\S*$', '') END AS text"
            "          FROM (SELECT CASE WHEN r.start > 1"
            "                THEN regexp_replace(r.raw, '^\\S*\\s+', '') ELSE r.raw END AS text) AS t) AS w)"
        )
        params = (
            self.config, *query_p,                       # to_tsvector(window) @@ query
            self.config, *query_p, options,              # window headline
            self.config, *body_p, *query_p, options,     # whole-body headline
            *body_p, list(self.words), self.config,      # the point
            *body_p,                                     # the window
        )
        return sql, params


def _search_postgres(ctx, qs):
    from django.contrib.postgres.search import SearchRank

    config = config_for(ctx.language)
    query = _query(ctx)

    # One definition of what each type matches against, shared with
    # count_by_type and page_by_type through _match and _pg_vector. These were
    # spelled out inline here, which is how the topic vector came to be wrong on
    # THIS path — the one readers actually hit — while a fix elsewhere would
    # have looked complete.
    def ranked(kind, *tiebreak):
        return (
            _match(kind, ctx, qs[kind])
            .annotate(
                rank=_ranked_expr(
                    kind, SearchRank(_pg_vector(kind, config, ctx.language), query), ctx
                )
            )
            .order_by("-rank", *tiebreak)
        )

    def entity(kind, builder):
        rows = ranked(kind)[: CAPS[kind]]
        return [(float(r.rank) * ENTITY_BOOST, builder(r, ctx)) for r in rows]

    def authors():
        # The people the query names come first, whatever their bios rank: a
        # bio that MENTIONS "D. L. Moody" (R. A. Torrey's) is not Moody.
        by_pk = {m.pk: m for m in ctx.people}
        named = list(
            ranked("author")
            .filter(pk__in=list(by_pk))
            .annotate(name_score=_name_order(ctx))
            .order_by("-name_score", "-rank")[: CAPS["author"]]
        )
        seen = {r.pk for r in named}
        others = [r for r in ranked("author")[: CAPS["author"]] if r.pk not in seen]
        scored = [
            (float(r.rank) * ENTITY_BOOST + _name_score(by_pk.get(r.pk)), r)
            for r in named + others
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [(score, _author_hit(r, ctx)) for score, r in scored[: CAPS["author"]]]

    snippet = _Snippet(
        F("body_text"), query, config, positive_words(ctx.q, ctx.language)
    )

    def passages(kind, builder, *tiebreak):
        # Computed in SQL on the capped rows only, so body_text is never loaded.
        rows = (
            ranked(kind, *tiebreak)
            .defer("body_text")
            .annotate(headline=snippet)[: CAPS[kind]]
        )
        return [(float(r.rank), builder(r, snippet=r.headline)) for r in rows]

    pairs: list[tuple[float, dict]] = []
    pairs += authors()
    pairs += entity("book", _book_hit)
    pairs += entity("topic", _topic_hit)
    pairs += entity("plan", _plan_hit)
    pairs += entity("article", _article_hit)
    with _index_scans(ctx.language):
        pairs += passages("chapter", _chapter_hit, "book__sort_order", "order")
        pairs += passages("sermon", _sermon_hit, "sort_order")

    pairs.sort(key=lambda pair: pair[0], reverse=True)
    return [hit for _, hit in pairs[:MAX_RESULTS]]


# --- Substring search (SQLite dev, and SUBSTRING_LANGUAGES) ---------------------


def _search_fallback(ctx, qs):
    """Substring search: SQLite (dev), and the SUBSTRING_LANGUAGES everywhere."""
    def rows(kind, *order):
        return _match(kind, ctx, qs[kind]).order_by(*order)[: CAPS[kind]]

    # The snippet centres on the first word; every word is in the row somewhere.
    lead = _snippet_term(ctx)
    results = (
        [
            _author_hit(a, ctx)
            for a in _match("author", ctx, qs["author"])
            .annotate(name_score=_name_order(ctx))
            .order_by("-name_score", "name")[: CAPS["author"]]
        ]
        + [_book_hit(b, ctx) for b in rows("book", "sort_order", "title")]
        + [_topic_hit(tp, ctx) for tp in rows("topic", "title")]
        + [_plan_hit(p, ctx) for p in rows("plan", "sort_order", "title")]
        + [_article_hit(ar, ctx) for ar in rows("article", "sort_order", "h1")]
        + [
            _chapter_hit(c, snippet=fallback_snippet(c.body_text, lead))
            for c in rows("chapter", "book__sort_order", "book__title", "order")
        ]
        + [
            _sermon_hit(sm, snippet=fallback_snippet(sm.body_text, lead))
            for sm in rows("sermon", "sort_order", "title")
        ]
    )
    # Entities first (navigational), then passages, capped overall.
    return results[:MAX_RESULTS]


# --- Counting and per-type pages ----------------------------------------------
# The merged list above is a *sample*: MAX_RESULTS and the per-type CAPS mean a
# search for "prayer" returns twenty passages out of hundreds, and nothing in the
# response said so — the page rendered "30 results", which reads as the whole
# library. These are how the reader gets the real number, and then the rest of
# one type when they ask for it.
#
# Both go through `_match`, so a count and the results it describes can never
# come from different filters.


def _terms(q: str, language: str) -> list[str]:
    """What a substring match looks for: the whole query on SQLite (dev, as it
    always has); in a SUBSTRING_LANGUAGE, each word the query is made OF
    (``positive_words``: no exclusions, no "OR", no stray punctuation)."""
    if language in SUBSTRING_LANGUAGES:
        return positive_words(q, language) or [q]
    return [q]


def _snippet_term(ctx) -> str:
    """The word a substring hit's snippet centres on: the first one matched."""
    return _terms(ctx.q, ctx.language)[0]


def _lite_match(kind: str, q: str, language: str) -> Q:
    """The substring predicate for ``q``.

    On SQLite (dev) the whole query, as it always was. In a SUBSTRING_LANGUAGE
    the websearch reading every other language gets from Postgres: each word
    must occur, ``OR`` joins its neighbours, ``-word`` excludes — tokenised by
    ``fts.query_tokens``, so the two paths agree on what the words are.
    """
    if language not in SUBSTRING_LANGUAGES:
        return _lite_q(kind, q, language)
    groups: list[Q] = []
    excluded: list[Q] = []
    pending_or = False
    for negated, word in query_tokens(q):
        if word.upper() == "OR" and not negated:
            pending_or = bool(groups)
            continue
        term = _lite_q(kind, word, language)
        if negated:
            excluded.append(term)
        elif pending_or:
            groups[-1] |= term
        else:
            groups.append(term)
        pending_or = False
    if not groups:
        # Nothing to match positively (an exclusion alone): as Postgres does.
        return _lite_q(kind, q, language)
    match = Q()
    for group in groups:
        match &= group
    for term in excluded:
        match &= ~term
    return match


def _lite_q(kind: str, q: str, language: str) -> Q:
    """The substring match predicate for one type, in ``language``."""
    if kind == "author":
        return Q(name__icontains=q) | Q(bio__icontains=q)
    if kind == "book":
        return (
            Q(title__icontains=q)
            | Q(subtitle__icontains=q)
            | Q(description__icontains=q)
            | Q(author__name__icontains=q)
        )
    if kind == "topic":
        # The text the reader is shown, as `_topic_localized` builds it for the
        # vector path: the row itself in English, else this language's
        # translation — never another language's, which no one here can read.
        if language == "en":
            return Q(title__icontains=q) | Q(description__icontains=q)
        return Q(translations__language=language) & (
            Q(translations__title__icontains=q)
            | Q(translations__description__icontains=q)
        )
    if kind == "plan":
        return Q(title__icontains=q) | Q(description__icontains=q)
    if kind == "article":
        return (
            Q(h1__icontains=q)
            | Q(meta_title__icontains=q)
            | Q(description__icontains=q)
        )
    if kind == "chapter":
        return (
            Q(body_text__icontains=q)
            | Q(title__icontains=q)
            | Q(book__title__icontains=q)
            | Q(book__subtitle__icontains=q)
            | Q(book__author__name__icontains=q)
        )
    return (
        Q(body_text__icontains=q)
        | Q(title__icontains=q)
        | Q(scripture_ref__icontains=q)
        | Q(author__name__icontains=q)
    )


def _topic_localized(language: str):
    """(title, description) expressions in the language the reader asked for.

    English lives in the Topic row itself; every other language lives in a
    TopicTranslation. There is deliberately NO English fallback (see
    backend/CLAUDE.md): a reader who asked for Swahili must not be handed
    English prose, and `_base_querysets` has already dropped topics with no
    title in this language — so an empty string is the honest value for a
    field this language has not translated, and it simply matches nothing.
    """
    if language == "en":
        return F("title"), F("description")

    def localized(field: str):
        return Coalesce(
            Subquery(
                TopicTranslation.objects.filter(
                    topic=OuterRef("pk"), language=language
                ).values(field)[:1]
            ),
            Value(""),
            # Explicit, because `title` is a CharField and `description` a
            # TextField: without it Django refuses to resolve the mixed types
            # and every non-English search raises. to_tsvector takes text
            # either way.
            output_field=TextField(),
        )

    return localized("title"), localized("description")


#: Types matched against a stored, GIN-indexed ``search_vector`` column (kept by
#: library/fts.py, with the same fields and weights the query-time vectors had)
#: instead of one rebuilt from the raw columns on every request. Authors and
#: topics are the exceptions: one row serves every language, and the reader's
#: language picks both the prose and the FTS config — see library/fts.py.
STORED = STORED_KINDS


def _pg_vector(kind: str, config: str, language: str):
    """The weighted vector a type matches against — stored where it can be."""
    from django.contrib.postgres.search import SearchVector

    if kind in STORED:
        return F("search_vector")

    def sv(field, weight):
        return SearchVector(field, weight=weight, config=config)

    if kind == "author":
        return sv("name", "A") + sv("bio", "C")
    if kind == "topic":
        # Topics are ONE row plus a TopicTranslation side-table, so `title` and
        # `description` are the ENGLISH columns whatever language was asked for.
        # Built from those, a Spanish reader searching "oración" never found the
        # prayer shelf, while the SQLite dev path — which does search
        # translations (`_lite_q`) — said it worked. Match the text the reader is
        # actually shown: TopicListSerializer renders `title_for(language)`.
        title, description = _topic_localized(language)
        return (
            SearchVector(title, weight="A", config=config)
            + SearchVector(description, weight="C", config=config)
        )
    raise ValueError(f"no query-time vector for {kind!r}")


def _match(kind: str, ctx, qs):
    """Rows of ``kind`` matching the query — unordered, un-paged."""
    # A person the query names is found by name, not only by the words of it
    # that full-text search can read (library/people.py).
    named = Q(pk__in=[m.pk for m in ctx.people]) if kind == "author" else Q(pk__in=[])
    if not uses_fts(ctx.language):
        predicate = _lite_match(kind, ctx.q, ctx.language) | named
        if ctx.corrected:
            predicate |= _lite_match(kind, ctx.corrected, ctx.language)
        person = ctx.person
        if person and kind in _AUTHOR_FIELD:
            # Their works, narrowed by whatever else was typed ("moody prayer").
            works = Q(**{_AUTHOR_FIELD[kind]: person.pk})
            if person.rest:
                works &= _lite_match(kind, " ".join(person.rest), ctx.language)
            predicate |= works
        book_slugs = [slug for slug, _ in ctx.aliased_books]
        if book_slugs and kind in ("book", "chapter"):
            field = "slug__in" if kind == "book" else "book__slug__in"
            predicate |= Q(**{field: book_slugs})
        matched = qs.filter(predicate)
        return matched.distinct() if kind == "topic" else matched

    query = _query(ctx)
    if kind in STORED:
        return qs.filter(search_vector=query)
    vector = _pg_vector(kind, config_for(ctx.language), ctx.language)
    return qs.annotate(search=vector).filter(Q(search=query) | named)


#: Ordering per type per sort mode. "relevance" isn't here: on Postgres it is the
#: rank annotation, and on SQLite there is no rank, so "natural" stands in.
_ORDER = {
    "author": {"title": ("name",), "newest": ("-created_at",), "natural": ("name",)},
    "book": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
    "topic": {"title": ("title",), "newest": ("-created_at",), "natural": ("title",)},
    "article": {
        "title": ("h1",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "h1"),
    },
    "plan": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
    "chapter": {
        "title": ("title", "order"),
        "newest": ("-book__created_at", "book__title", "order"),
        "natural": ("book__sort_order", "book__title", "order"),
    },
    "sermon": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
}

SORTS = ("relevance", "title", "newest")


def count_by_type(q: str, language: str, scope=None) -> tuple[dict, dict]:
    """(counts, capped) per type — how many matches actually exist.

    Counting stops at ``COUNT_CEILING`` and ``capped[kind]`` says when it did, so
    the reader is shown "200+" rather than a number we didn't finish computing.
    Slicing before ``.count()`` puts the LIMIT inside the subquery, so the
    database stops scanning once it has enough.
    """
    ctx = _Ctx(q=q, language=language)
    counts: dict[str, int] = {}
    capped: dict[str, bool] = {}
    querysets = _base_querysets(language, scope)

    def tally(kind):
        n = _match(kind, ctx, querysets[kind]).values("pk")[:COUNT_CEILING].count()
        if n:
            counts[kind] = n
            capped[kind] = n >= COUNT_CEILING

    # In _base_querysets' order either way, so the totals serialise stably.
    for kind in querysets:
        if kind not in TOASTED:
            tally(kind)
    with _index_scans(language):
        for kind in querysets:
            if kind in TOASTED:
                tally(kind)
    for kind, n in (
        ("quote", len(quote_hits(q, language, ctx.writer, scope))),
        ("answer", len(answer_hits(q, language, scope))),
    ):
        if n:
            counts[kind] = n
            capped[kind] = False
    # "scripture" is intentionally uncounted: it has no queryset, and a reference
    # resolves to 0-or-1 page, so the frontend's `totals[type] ?? loaded` fallback
    # lands on the single loaded row exactly. Counting it would mean re-running
    # the resolver here for no gain.
    return counts, capped


def _pg_rank_order(kind, ctx, qs):
    from django.contrib.postgres.search import SearchRank

    config = config_for(ctx.language)
    vector = _pg_vector(kind, config, ctx.language)
    qs = qs.annotate(rank=_ranked_expr(kind, SearchRank(vector, _query(ctx)), ctx))
    if kind == "author":
        return qs.annotate(name_score=_name_order(ctx)).order_by(
            "-name_score", "-rank", *_ORDER[kind]["natural"]
        )
    return qs.order_by("-rank", *_ORDER[kind]["natural"])


def page_by_type(
    q: str,
    language: str,
    kind: str,
    *,
    offset: int = 0,
    limit: int = PAGE_SIZE,
    sort: str = "relevance",
    scope=None,
) -> list[dict]:
    """One type's matches, ordered and paged — the "show more" path.

    Sorting lives here rather than in the browser for the reason the whole change
    exists: the client could only ever reorder the rows it had been handed, so
    "newest" meant "newest of the thirty most relevant". Ordering the full match
    set is the only way that control can mean what it says.
    """
    # Scripture is a reference-triggered hit with no queryset behind it (see
    # _scripture_page_hits), so it can't go through _match/_base_querysets. There
    # is at most one page per query, so paging is trivial — this exists only so
    # the type facet's "show this kind" fetch returns the hit rather than blank.
    if kind == "scripture":
        ref = verse_quoted(q, language) or q
        return _scripture_page_hits(ref, language, scope)[offset : offset + limit]
    if kind == "answer":
        return answer_hits(q, language, scope)[offset : offset + limit]
    if kind == "quote":
        ctx = _Ctx(q=q, language=language)
        hits = quote_hits(q, language, ctx.writer, scope)
        if sort == "title":
            hits.sort(key=lambda h: h["text"].casefold())
        return hits[offset : offset + limit]
    if kind not in CAPS:
        return []
    ctx = _Ctx(q=q, language=language)
    qs = _match(kind, ctx, _base_querysets(language, scope)[kind])

    if sort in ("title", "newest"):
        qs = qs.order_by(*_ORDER[kind][sort])
    elif uses_fts(language):
        qs = _pg_rank_order(kind, ctx, qs)
    else:
        if kind == "author":
            qs = qs.annotate(name_score=_name_order(ctx))
        qs = qs.order_by(*(("-name_score",) if kind == "author" else ()), *_ORDER[kind]["natural"])

    with _index_scans(language) if kind in TOASTED else nullcontext():
        return [_hit_for(kind, row, ctx) for row in qs[offset : offset + limit]]


def _hit_for(kind: str, row, ctx) -> dict:
    """Build a hit for a paged row, with the same snippet the merged list uses."""
    if kind == "author":
        return _author_hit(row, ctx)
    if kind == "book":
        return _book_hit(row, ctx)
    if kind == "topic":
        return _topic_hit(row, ctx)
    if kind == "plan":
        return _plan_hit(row, ctx)
    if kind == "article":
        return _article_hit(row, ctx)
    snippet = fallback_snippet(getattr(row, "body_text", ""), _snippet_term(ctx))
    return _chapter_hit(row, snippet) if kind == "chapter" else _sermon_hit(row, snippet)


# --- Hit builders -------------------------------------------------------------


def _date(dt) -> str:
    """A hit's publish date as an ISO ``YYYY-MM-DD`` string (for the "newest"
    client sort), or "" when absent. Date-only on purpose: enough to order by,
    without leaking exact ingest timestamps."""
    return dt.date().isoformat() if dt else ""


def _author_hit(a, ctx):
    person = next((m for m in ctx.people if m.pk == a.pk), None)
    hit = {
        "type": "author",
        "author_slug": a.slug,
        "author_name": a.name,
        # A face and a cover make a list of titles scannable. Both may be blank,
        # and the client renders text-only when they are — no placeholder, which
        # would only add noise to a row that reads fine without one.
        "photo_url": a.photo_url,
        # Found by name, the bio opens on the name rather than on the first
        # "d" of "d l moody".
        "snippet": fallback_snippet(
            a.bio_for(ctx.language),
            person.surname if person and person.by_surname else _snippet_term(ctx),
        ),
        "date": _date(a.created_at),
    }
    if person and person.named:
        # The query IS this person's name, however it was spelt — the client
        # leads with them as it would with an exact title (topResult).
        hit["named"] = True
    return hit


def _book_hit(b, ctx):
    return {
        "type": "book",
        "book_slug": b.slug,
        "book_title": b.title,
        "author_name": b.author.name,
        "cover_url": b.cover_url,
        # The cover's dominant colour, so the reserved box is filled with
        # something of the book's own while the image loads — and stays filled
        # if it never does. Reserving the space is what stops the list reflowing
        # under the reader's cursor.
        "cover_color": b.cover_color,
        # What the thumbnail's type needs: a plate is a wordless ground.
        "cover": cover_face(b),
        "snippet": fallback_snippet(b.description, _snippet_term(ctx)),
        "date": _date(b.created_at),
    }


def _topic_hit(tp, ctx):
    return {
        "type": "topic",
        "topic_slug": tp.slug,
        "topic_title": tp.title_for(ctx.language),
        "snippet": fallback_snippet(tp.description_for(ctx.language), _snippet_term(ctx)),
        "date": _date(tp.created_at),
    }


def _plan_hit(p, ctx):
    return {
        "type": "plan",
        "plan_slug": p.slug,
        "plan_title": p.title,
        "snippet": fallback_snippet(p.description, _snippet_term(ctx)),
        "date": _date(p.created_at),
    }


def _article_hit(a, ctx):
    # An article has no author and no cover, so — like a topic or a plan — the
    # row is title + snippet, no image. `h1` is the display headline; the
    # snippet comes from the standfirst (`description`), the only prose that
    # isn't HTML (there is no `body_text` on an Article to excerpt).
    return {
        "type": "article",
        "article_slug": a.slug,
        "article_title": a.h1,
        "snippet": fallback_snippet(a.description, _snippet_term(ctx)),
        "date": _date(a.created_at),
    }


def _chapter_hit(c, snippet):
    # Chapters have no date of their own; a chapter is as old as its book.
    return {
        "type": "chapter",
        "book_slug": c.book.slug,
        "book_title": c.book.title,
        "author_name": c.book.author.name,
        "chapter_order": c.order,
        "chapter_title": c.title,
        "cover_url": c.book.cover_url,
        "cover_color": c.book.cover_color,
        "cover": cover_face(c.book),
        "snippet": snippet,
        "date": _date(c.book.created_at),
    }


def _sermon_hit(s, snippet):
    return {
        "type": "sermon",
        "sermon_slug": s.slug,
        "sermon_title": s.title,
        "author_name": s.author.name,
        "scripture_ref": s.scripture_ref,
        "snippet": snippet,
        "date": _date(s.created_at),
    }


def _lead(text: str, n: int = 160) -> str:
    """A plain lead excerpt (no highlight markers) for scripture-match snippets,
    whose query is a reference, not words found in the body."""
    text = (text or "").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _scripture_page_hits(q, language, scope=None):
    """The scripture HUB page for a reference query, when one has earned a URL.

    Reference-triggered like ``_scripture_sermon_hits`` / ``_scripture_chapter_hits``
    (returns [] when ``q`` isn't a reference), but a single NAVIGATIONAL result:
    a link to the ``/scripture/<book>/<chapter>[/<verse>]`` page that gathers
    everything treating the passage, led above those individual passages. The
    row carries no prose (the page is an aggregation) and no date to sort by; the
    client builds the link from book_slug/chapter/verse, as the page chips do.

    ``scripture_graph.pages_for`` is the one floor-respecting resolver (the same
    rule the pages, sitemap and inline links use), so a hit is emitted only where
    the page was actually built — never a link to a 404. Scripture pages are
    English-only (built from English citations, ASV text) and are global hubs, so
    nothing fires for a non-English reader or inside a scope — mirroring how the
    footer and command palette gate ``/scripture``.

    Returns AT MOST ONE hit — a query resolves to a single page. That invariant
    is load-bearing downstream: scripture is deliberately absent from ``CAPS`` and
    ``count_by_type`` (it has no queryset), so the facet's count falls back to the
    one loaded row, which is exact only because the count is 0-or-1.
    """
    if scope or language != "en":
        return []
    from .scripture_graph import book_from_slug, pages_for, reference_label

    page = pages_for([q]).get(q)
    if not page:
        return []
    book = book_from_slug(page["book"])
    verse = page.get("verse")
    return [
        {
            "type": "scripture",
            "book_slug": page["book"],
            "chapter": page["chapter"],
            "verse": verse,
            "reference": reference_label(book, page["chapter"], verse) if book else "",
            "snippet": "",
            "date": "",
        }
    ]


def _scripture_sermon_hits(q, sermons, base):
    """Sermons whose ``scripture_ref`` overlaps the query's referenced verses.

    Returns [] when ``q`` isn't a scripture reference. Deduped against sermons
    already present in ``base`` so a sermon found by text search isn't repeated.

    Two-phase, like ``_scripture_chapter_hits``: the reference test only needs
    ``scripture_ref``, so the scan runs over row values and only the winners are
    fetched as instances. Iterating instances pulled every published sermon's
    ``body_html``, ``body_text`` and tsvector into memory to read one short
    field off each — for every query containing a verse number, i.e. per
    keystroke once the reader types a digit.
    """
    target = reference_verse_ids(q)
    if not target:
        return []
    already = {h["sermon_slug"] for h in base if h["type"] == "sermon"}
    winners = []
    for row in (
        sermons.exclude(scripture_ref="")
        .order_by("sort_order", "title")
        .values("pk", "slug", "scripture_ref")
    ):
        if row["slug"] in already:
            continue
        if reference_verse_ids(row["scripture_ref"]) & target:
            winners.append(row["pk"])
            if len(winners) >= CAPS["sermon"]:
                break
    if not winners:
        return []
    # Fetched in one query, then put back into the order the scan chose — an
    # `pk__in` fetch returns rows in whatever order the database likes.
    by_pk = {
        s.pk: s
        for s in Sermon.objects.filter(pk__in=winners)
        .select_related("author")
        .defer("body_html", "search_vector")
    }
    return [
        _sermon_hit(by_pk[pk], snippet=_lead(by_pk[pk].body_text))
        for pk in winners
        if pk in by_pk
    ]


def _scripture_chapter_hits(q, chapters):
    """Chapters whose body cites a reference overlapping the query's verses.

    Takes the eligible ``chapters`` queryset rather than re-deriving it, so the
    citation lead is published/language-filtered and SCOPED exactly like every
    other kind of hit — searching inside one book must not surface a citation
    from another.

    The verse-id range filter is only a PREFILTER: a multi-reference query
    ("John 3:16 and Romans 8:28") spans two books, and everything cited in
    between falls inside min..max — so rows are re-checked against the exact
    verse-id set before ranking (the same set-intersection contract as
    _scripture_sermon_hits). Bare book names ("Matthew") parse as whole-book
    references and would bury the text results under twenty incidental
    citations, so the citation lead requires a chapter-or-verse query (a
    digit). Row values first, winner chapters fetched after — a whole-book
    prefilter can match hundreds of rows, and dragging each chapter's body
    through the join costs tens of MB (measured 40 MB for "Matthew").
    """
    if not any(ch.isdigit() for ch in q):
        return []
    target = reference_verse_ids(q)
    if not target:
        return []
    rows = ChapterCitation.objects.filter(
        start_verse_id__lte=max(target),
        end_verse_id__gte=min(target),
        chapter__in=chapters.values("pk"),
    ).values("chapter_id", "start_verse_id", "end_verse_id", "count", "ref_text")
    matches = [
        r
        for r in rows
        if not target.isdisjoint(range(r["start_verse_id"], r["end_verse_id"] + 1))
    ]
    # Narrowest citation first (most specific), then most-repeated; one pass
    # keeps each chapter's best row via insertion order.
    best: dict[int, dict] = {}
    for r in sorted(
        matches, key=lambda r: (r["end_verse_id"] - r["start_verse_id"], -r["count"])
    ):
        best.setdefault(r["chapter_id"], r)
    winners = list(best.values())[: CAPS["chapter"]]
    chapters = {
        c.pk: c
        for c in Chapter.objects.filter(pk__in=[w["chapter_id"] for w in winners])
        .select_related("book__author")
        .defer("body_html", "search_vector", "book__search_vector")
    }
    return [
        _chapter_hit(
            chapters[w["chapter_id"]],
            snippet=fallback_snippet(
                chapters[w["chapter_id"]].body_text or "", w["ref_text"]
            ),
        )
        for w in winners
        if w["chapter_id"] in chapters
    ]


# --- Typo forgiveness ----------------------------------------------------------
# A did-you-mean only helps once a search has come back EMPTY, and only after
# the reader taps it. "humilty prayer" found the prayer passages and never said
# that Murray's Humility was one letter away. So a misspelt word is corrected in
# the search itself: the query runs as typed OR as corrected, and the response
# says what else it searched for.

#: Words shorter than this are left alone: too many real words sit one letter
#: from each other ("hope"/"hops"), and short typos are rarely the problem.
CORRECT_MIN_LEN = 4
#: difflib ratio a correction must reach ("humilty" -> "humility" is 0.93,
#: "sorry" -> "worry" 0.8 — so the bar sits just above that).
CORRECT_CUTOFF = 0.82
_TITLE_WORD = re.compile(rf"[^\W\d_]{{{CORRECT_MIN_LEN},}}", re.UNICODE)


def _title_vocabulary(language: str) -> list[str]:
    """The words a correction may correct TO: those of this language's book,
    plan, article and topic titles (and book subtitles). Titles, not bodies:
    they are what a reader is usually trying to name, and a vocabulary of a few
    thousand words keeps difflib fast."""

    def compute():
        vocab: set[str] = set()

        def add(text):
            vocab.update(w.lower() for w in _TITLE_WORD.findall(text or ""))

        for title, subtitle in Book.objects.filter(
            is_published=True, language=language
        ).values_list("title", "subtitle"):
            add(title)
            add(subtitle)
        for title in Plan.objects.filter(is_published=True, language=language).values_list(
            "title", flat=True
        ):
            add(title)
        for h1 in Article.objects.filter(is_published=True, language=language).values_list(
            "h1", flat=True
        ):
            add(h1)
        if language == "en":
            topics = Topic.objects.filter(is_published=True).values_list("title", flat=True)
        else:
            topics = TopicTranslation.objects.filter(
                language=language, topic__is_published=True
            ).values_list("title", flat=True)
        for title in topics:
            add(title)
        return sorted(vocab)

    return memoized("title-vocabulary", compute, language)


def _in_library(word: str, language: str) -> bool:
    """Whether ``word`` occurs anywhere in this language's text — then it is a
    real word the reader meant, not a typo, however far from any title."""
    if uses_fts(language):
        query = search_query(word, language)
        return (
            Chapter.objects.filter(
                book__is_published=True, book__language=language, search_vector=query
            ).exists()
            or Sermon.objects.filter(
                is_published=True, language=language, search_vector=query
            ).exists()
        )
    return Chapter.objects.filter(
        book__is_published=True, book__language=language, body_text__icontains=word
    ).exists()


def correction(q: str, language: str) -> str | None:
    """``q`` with its misspelt words corrected to title words, or None.

    A word is corrected only when it is long enough, isn't a title word, occurs
    nowhere in the library, and lies close to exactly-ish one title word. Not in
    the substring and prefix languages (Japanese, Korean), where a "word" is not
    a unit difflib can judge. Exclusions and OR stay as typed.
    """
    if language in SUBSTRING_LANGUAGES or language in PREFIX_LANGUAGES:
        return None

    def compute():
        vocab = _title_vocabulary(language)
        known = set(vocab)
        # A title word typed without its accents ("oracion", "priere") is the
        # word itself, whatever else the library holds.
        unaccented = {fold(w): w for w in vocab if fold(w) != w}
        fixed: dict[str, str] = {}
        for negated, word in query_tokens(q):
            low = word.lower()
            if (
                negated
                or word == "OR"
                or len(low) < CORRECT_MIN_LEN
                or not low.isalpha()
                or low in known
                or low in fixed
            ):
                continue
            if low in unaccented:
                fixed[low] = unaccented[low]
                continue
            close = difflib.get_close_matches(low, vocab, n=1, cutoff=CORRECT_CUTOFF)
            if close and not _in_library(word, language):
                fixed[low] = close[0]
        if not fixed:
            return None
        return re.sub(
            r"\w+",
            lambda m: fixed.get(m.group(0).lower(), m.group(0)),
            q,
        )

    return memoized("correction", compute, q, language)


# --- Did-you-mean -------------------------------------------------------------

_SUGGEST_CUTOFF = 0.72
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)


def suggest(q: str, language: str) -> str | None:
    """Closest library term to a query that found nothing — the "did you mean".

    Fuzzy-matches (difflib, DB-agnostic) against a small vocabulary of author
    names and book/topic/plan titles plus their significant words, so a
    misspelt author ("Spurgen") or title ("humilty") resolves. Returns None
    when nothing is close enough or the best match is the query itself.
    """
    ql = q.strip().lower()
    if len(ql) < 3:
        return None

    # search-key (lowercased) -> display term, deduped. Each source string
    # contributes itself and its individual long words, so a surname buried in
    # a full name is reachable.
    vocab: dict[str, str] = {}

    def add(s: str) -> None:
        if not s:
            return
        vocab.setdefault(s.lower(), s)
        for w in _WORD.findall(s):
            vocab.setdefault(w.lower(), w)

    names = (
        Author.objects.filter(
            Q(books__is_published=True, books__language=language)
            | Q(sermons__is_published=True, sermons__language=language)
        )
        .distinct()
        .values_list("name", flat=True)
    )
    for name in names:
        add(name)
    for title in Book.objects.filter(
        is_published=True, language=language
    ).values_list("title", flat=True):
        add(title)
    for title in Plan.objects.filter(
        is_published=True, language=language
    ).values_list("title", flat=True):
        add(title)
    for h1 in Article.objects.filter(
        is_published=True, language=language
    ).values_list("h1", flat=True):
        add(h1)
    for title in Topic.objects.filter(is_published=True).values_list(
        "title", flat=True
    ):
        add(title)

    best = difflib.get_close_matches(ql, list(vocab), n=1, cutoff=_SUGGEST_CUTOFF)
    if not best or best[0] == ql:
        return None
    return vocab[best[0]]


# A search hit reduced to the translatable WORK behind it, named the way the
# translation queue names it: a chapter is its book; an author is a bio job.
# type -> (job_type, slug field, title field) on the hit.
HIT_WORK = {
    "book": ("book", "book_slug", "book_title"),
    "chapter": ("book", "book_slug", "book_title"),
    "sermon": ("sermon", "sermon_slug", "sermon_title"),
    "plan": ("plan", "plan_slug", "plan_title"),
    "author": ("bio", "author_slug", "author_name"),
    "topic": ("topic", "topic_slug", "topic_title"),
    "article": ("article", "article_slug", "article_title"),
}


def hit_work(hit: dict) -> dict | None:
    """One search hit as a queueable work, or None for a hit that isn't one
    (a scripture navigational row, or anything missing a slug)."""
    spec = HIT_WORK.get(hit.get("type"))
    if spec is None:
        return None
    job_type, slug_key, title_key = spec
    slug = hit.get(slug_key)
    if not slug:
        return None
    return {"type": job_type, "slug": slug, "title": hit.get(title_key) or slug}
