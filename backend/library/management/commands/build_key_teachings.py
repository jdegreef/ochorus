"""Build the *Key Teachings of …* series — Ochorus's own study companions.

These are NOT the authors' own texts. Each is an independent, house-written
work of exposition and appreciation that distills a classic teacher's message
into a short run of chapters (each ending in questions and a prayer), quoting
only the Authorised (King James) Version and naming the author's own works for
further reading. That design is what lets the series cover writers whose actual
books are still in copyright (Watchman Nee) as safely as it covers the
public-domain ones (Simpson, Edwards, Baxter): nothing of the author's own prose
is reproduced — only Ochorus's summaries and KJV Scripture.

A companion is BY the house: its author is ``ochorus-originals``, because the
person it is about did not write it (an earlier build filed it under that
person, which put "The Key Teachings of A. B. Simpson" on Simpson's shelf, and
into his schema.org authorship, as if he had). The person is kept in two places:
``cover_byline`` sets their name across the top of the cover, as it always was,
and ``book_people_seed.BOOK_PEOPLE`` makes them the book's lone subject, which
files it under "Books about" on their author page. ``Work.author_slug`` names
that person. ``tests_originals_series.py`` holds all three together.

Every volume is a Markdown manuscript, ``data/key-teachings/<author>.md``
(grammar at ``manuscript``), with its description and "About this work" in the
front matter. The first four (Simpson, Edwards, Baxter, Nee) were first built
from PDFs set in one template; in 2026-09 they were converted, text unchanged,
to manuscripts like the rest, so every volume can be edited — and reshaped —
the same way (git history holds the PDF reader).

Fixture-driven: ``seed_books`` creates each book (and resolves the author from
``authors.json``) on the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_key_teachings                # all
    DJANGO_DEBUG=true uv run python manage.py build_key_teachings key-teachings-of-a-b-simpson
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter, Series
from library.titlecase import recase_title

DATA_DIR = Path(__file__).resolve().parent / "data" / "key-teachings"

@dataclass(frozen=True)
class Work:
    slug: str
    title: str
    subtitle: str
    author_slug: str  # the person it is ABOUT — its subject, not its author
    source: str  # the Markdown manuscript under DATA_DIR; its front matter
    # carries the reader-visible description and "About this work"
    attribution: str
    cover_color: str

    @property
    def cover_url(self) -> str:
        # The painted "study" ground (#4500), which replaced the series' first
        # gilt-tree SVGs; wordless, so BookCover sets the title over it.
        return f"/covers/art/{self.slug}.jpg"


WORKS: dict[str, Work] = {
    "key-teachings-of-a-b-simpson": Work(
        slug="key-teachings-of-a-b-simpson",
        title="The Key Teachings of A. B. Simpson",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="a-b-simpson",
        source="a-b-simpson.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus — not published by, affiliated with, or endorsed by The "
            "Christian and Missionary Alliance or any body descended from "
            "Simpson's ministry. A. B. Simpson's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#1f5468",
    ),
    "key-teachings-of-jonathan-edwards": Work(
        slug="key-teachings-of-jonathan-edwards",
        title="The Key Teachings of Jonathan Edwards",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="jonathan-edwards",
        source="jonathan-edwards.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Jonathan Edwards's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version, "
            "the version Edwards preached from."
        ),
        cover_color="#2f4a34",
    ),
    "key-teachings-of-richard-baxter": Work(
        slug="key-teachings-of-richard-baxter",
        title="The Key Teachings of Richard Baxter",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="richard-baxter",
        source="richard-baxter.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Richard Baxter's own writings are in the public domain; his "
            "seventeenth-century English has been rendered into modern prose "
            "rather than quoted, and readers are encouraged to go to the originals "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#5b2f2a",
    ),
    "key-teachings-of-watchman-nee": Work(
        slug="key-teachings-of-watchman-nee",
        title="The Key Teachings of Watchman Nee",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="watchman-nee",
        source="watchman-nee.md",
        # Nee's own works are NOT public domain — this companion quotes only the
        # KJV and paraphrases; the disavowal below is essential and must ship.
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by any "
            "organisation holding rights in the writings of Watchman Nee. All "
            "descriptions of his teaching are the present author's own summaries; "
            "his books and spoken ministry are named for further study, and "
            "readers are warmly encouraged to obtain those works from their "
            "rightful publishers. Scripture quotations are from the Authorised "
            "(King James) Version."
        ),
        cover_color="#2a3a5e",
    ),
    "key-teachings-of-charles-h-spurgeon": Work(
        slug="key-teachings-of-charles-h-spurgeon",
        title="The Key Teachings of Charles H. Spurgeon",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="charles-h-spurgeon",
        source="charles-h-spurgeon.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Not published by, affiliated with, or endorsed by the Metropolitan "
            "Tabernacle or Spurgeon's College. Charles H. Spurgeon's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#43305a",
    ),
    "key-teachings-of-andrew-murray": Work(
        slug="key-teachings-of-andrew-murray",
        title="The Key Teachings of Andrew Murray",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="andrew-murray",
        source="andrew-murray.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Andrew Murray's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#4a5a2a",
    ),
    "key-teachings-of-hannah-whitall-smith": Work(
        slug="key-teachings-of-hannah-whitall-smith",
        title="The Key Teachings of Hannah Whitall Smith",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="hannah-whitall-smith",
        source="hannah-whitall-smith.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Hannah Whitall Smith's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#4a5a6c",
    ),
    "key-teachings-of-catherine-booth": Work(
        slug="key-teachings-of-catherine-booth",
        title="The Key Teachings of Catherine Booth",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="catherine-booth",
        source="catherine-booth.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Not published by, affiliated with, or endorsed by The Salvation "
            "Army. Catherine Booth's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#7c2436",
    ),
    "key-teachings-of-augustine-of-hippo": Work(
        slug="key-teachings-of-augustine-of-hippo",
        title="The Key Teachings of Augustine of Hippo",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="augustine-of-hippo",
        source="augustine-of-hippo.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Augustine wrote in Latin; where his words are quoted, it is in "
            "public-domain English translations. Augustine's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#7b5a2c",
    ),
    "key-teachings-of-amanda-berry-smith": Work(
        slug="key-teachings-of-amanda-berry-smith",
        title="The Key Teachings of Amanda Berry Smith",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="amanda-berry-smith",
        source="amanda-berry-smith.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Amanda Berry Smith's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#5a1a6a",
    ),
    "key-teachings-of-hudson-taylor": Work(
        slug="key-teachings-of-hudson-taylor",
        title="The Key Teachings of Hudson Taylor",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="hudson-taylor",
        source="hudson-taylor.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. "
            "Not published by, affiliated with, or endorsed by OMF International. Hudson Taylor's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#1f6a5a",
    ),
    "key-teachings-of-athanasius-of-alexandria": Work(
        slug="key-teachings-of-athanasius-of-alexandria",
        title="The Key Teachings of Athanasius of Alexandria",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="athanasius-of-alexandria",
        source="athanasius-of-alexandria.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. "
            "Athanasius wrote in Greek; where his words are quoted, it is in public-domain English translations. Athanasius's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#1f4a9a",
    ),
    "key-teachings-of-julia-foote": Work(
        slug="key-teachings-of-julia-foote",
        title="The Key Teachings of Julia A. J. Foote",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="julia-foote",
        source="julia-foote.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Julia A. J. Foote's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#9a4a1a",
    ),
    "key-teachings-of-jeanne-guyon": Work(
        slug="key-teachings-of-jeanne-guyon",
        title="The Key Teachings of Jeanne Guyon",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="jeanne-guyon",
        source="jeanne-guyon.md",
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. "
            "Madame Guyon wrote in French; where her words are quoted, it is in a public-domain English translation. Jeanne Guyon's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#3a2a22",
    ),
    "key-teachings-of-r-a-torrey": Work(
        slug="key-teachings-of-r-a-torrey",
        title="The Key Teachings of R. A. Torrey",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="r-a-torrey",
        source="r-a-torrey.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. R. A. Torrey's own writings are in the public domain and "
            "freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#1a3ab0",
    ),
    "key-teachings-of-dwight-l-moody": Work(
        slug="key-teachings-of-dwight-l-moody",
        title="The Key Teachings of Dwight L. Moody",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="dwight-l-moody",
        source="dwight-l-moody.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Not published by, affiliated with, or endorsed by the "
            "Moody Bible Institute or Moody Church. Dwight L. Moody's own "
            "writings are in the public domain and freely available; readers "
            "are encouraged to go to them directly. Scripture quotations are "
            "from the Authorised (King James) Version."
        ),
        cover_color="#1f7f1f",
    ),
    "key-teachings-of-john-bunyan": Work(
        slug="key-teachings-of-john-bunyan",
        title="The Key Teachings of John Bunyan",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="john-bunyan",
        source="john-bunyan.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. John Bunyan's own writings are in the public domain and "
            "freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#0a3a1a",
    ),
    "key-teachings-of-john-wesley": Work(
        slug="key-teachings-of-john-wesley",
        title="The Key Teachings of John Wesley",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="john-wesley",
        source="john-wesley.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Not published by, affiliated with, or endorsed by any "
            "Methodist church or body. John Wesley's own writings are in the "
            "public domain and freely available; readers are encouraged to go "
            "to them directly. Scripture quotations are from the Authorised "
            "(King James) Version."
        ),
        cover_color="#8a0a1a",
    ),
    "key-teachings-of-charles-finney": Work(
        slug="key-teachings-of-charles-finney",
        title="The Key Teachings of Charles G. Finney",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="charles-finney",
        source="charles-finney.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Charles G. Finney's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King "
            "James) Version."
        ),
        cover_color="#990f82",
    ),
    "key-teachings-of-john-owen": Work(
        slug="key-teachings-of-john-owen",
        title="The Key Teachings of John Owen",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="john-owen",
        source="john-owen.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. His seventeenth-century English has been rendered into "
            "modern prose except where briefly quoted. John Owen's own writings "
            "are in the public domain and freely available; readers are "
            "encouraged to go to them directly. Scripture quotations are from "
            "the Authorised (King James) Version."
        ),
        cover_color="#7f1f4f",
    ),
    "key-teachings-of-e-m-bounds": Work(
        slug="key-teachings-of-e-m-bounds",
        title="The Key Teachings of E. M. Bounds",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="e-m-bounds",
        source="e-m-bounds.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. E. M. Bounds's own writings are in the public domain and "
            "freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#0a0a2a",
    ),
    "key-teachings-of-frederick-brotherton-meyer": Work(
        slug="key-teachings-of-frederick-brotherton-meyer",
        title="The Key Teachings of F. B. Meyer",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="frederick-brotherton-meyer",
        source="frederick-brotherton-meyer.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. F. B. Meyer's own writings are in the public domain and "
            "freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#30102a",
    ),
    "key-teachings-of-george-whitefield": Work(
        slug="key-teachings-of-george-whitefield",
        title="The Key Teachings of George Whitefield",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="george-whitefield",
        source="george-whitefield.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. George Whitefield's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King "
            "James) Version."
        ),
        cover_color="#4a6a00",
    ),
    "key-teachings-of-ignatius-of-antioch": Work(
        slug="key-teachings-of-ignatius-of-antioch",
        title="The Key Teachings of Ignatius of Antioch",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="ignatius-of-antioch",
        source="ignatius-of-antioch.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Ignatius wrote in Greek; where his words are quoted, it "
            "is in a public-domain English translation. Ignatius's own writings "
            "are in the public domain and freely available; readers are "
            "encouraged to go to them directly. Scripture quotations are from "
            "the Authorised (King James) Version."
        ),
        cover_color="#856818",
    ),
    "key-teachings-of-john-calvin": Work(
        slug="key-teachings-of-john-calvin",
        title="The Key Teachings of John Calvin",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="john-calvin",
        source="john-calvin.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Calvin wrote in Latin and French; where his words are "
            "quoted, it is in public-domain English translations. John Calvin's "
            "own writings are in the public domain and freely available; "
            "readers are encouraged to go to them directly. Scripture "
            "quotations are from the Authorised (King James) Version."
        ),
        cover_color="#002db7",
    ),
    "key-teachings-of-martin-luther": Work(
        slug="key-teachings-of-martin-luther",
        title="The Key Teachings of Martin Luther",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="martin-luther",
        source="martin-luther.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Luther wrote in German and Latin; where his words are "
            "quoted, it is in public-domain English translations. Martin "
            "Luther's own writings are in the public domain and freely "
            "available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#1f1f7f",
    ),
    # A. W. Tozer's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-a-w-tozer": Work(
        slug="key-teachings-of-a-w-tozer",
        title="The Key Teachings of A. W. Tozer",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="a-w-tozer",
        source="a-w-tozer.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of A. W. Tozer. "
            "All descriptions of his teaching are the present author's own "
            "summaries; his books and spoken ministry are named for further "
            "study, and readers are warmly encouraged to obtain those works "
            "from their rightful publishers. Scripture quotations are from the "
            "Authorised (King James) Version."
        ),
        cover_color="#3a1a4a",
    ),
    # Martyn Lloyd-Jones's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-martyn-lloyd-jones": Work(
        slug="key-teachings-of-martyn-lloyd-jones",
        title="The Key Teachings of Martyn Lloyd-Jones",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="martyn-lloyd-jones",
        source="martyn-lloyd-jones.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of Martyn Lloyd- "
            "Jones. All descriptions of his teaching are the present author's "
            "own summaries; his books and spoken ministry are named for further "
            "study, and readers are warmly encouraged to obtain those works "
            "from their rightful publishers. Scripture quotations are from the "
            "Authorised (King James) Version."
        ),
        cover_color="#007689",
    ),
    # Corrie ten Boom's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-corrie-ten-boom": Work(
        slug="key-teachings-of-corrie-ten-boom",
        title="The Key Teachings of Corrie ten Boom",
        subtitle="An Ochorus companion to her life and teaching",
        author_slug="corrie-ten-boom",
        source="corrie-ten-boom.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of Corrie ten "
            "Boom. All descriptions of her teaching are the present author's "
            "own summaries; her books and spoken ministry are named for further "
            "study, and readers are warmly encouraged to obtain those works "
            "from their rightful publishers. Scripture quotations are from the "
            "Authorised (King James) Version."
        ),
        cover_color="#b02a2a",
    ),
    # Derek Prince's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-derek-prince": Work(
        slug="key-teachings-of-derek-prince",
        title="The Key Teachings of Derek Prince",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="derek-prince",
        source="derek-prince.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of Derek Prince. "
            "All descriptions of his teaching are the present author's own "
            "summaries; his books and spoken ministry are named for further "
            "study, and readers are warmly encouraged to obtain those works "
            "from their rightful publishers. Scripture quotations are from the "
            "Authorised (King James) Version."
        ),
        cover_color="#1f7f4f",
    ),
    # Dietrich Bonhoeffer's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-dietrich-bonhoeffer": Work(
        slug="key-teachings-of-dietrich-bonhoeffer",
        title="The Key Teachings of Dietrich Bonhoeffer",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="dietrich-bonhoeffer",
        source="dietrich-bonhoeffer.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of Dietrich "
            "Bonhoeffer. All descriptions of his teaching are the present "
            "author's own summaries; his books and spoken ministry are named "
            "for further study, and readers are warmly encouraged to obtain "
            "those works from their rightful publishers. Scripture quotations "
            "are from the Authorised (King James) Version."
        ),
        cover_color="#5a1aa0",
    ),
    # Gareth Evans's own works are NOT public domain — this companion quotes only the
    # KJV and paraphrases; the disavowal is essential and must ship.
    "key-teachings-of-gareth-evans": Work(
        slug="key-teachings-of-gareth-evans",
        title="The Key Teachings of Gareth Evans",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="gareth-evans",
        source="gareth-evans.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "any organisation holding rights in the writings of Gareth Evans. "
            "All descriptions of his teaching are the present author's own "
            "summaries; his books and spoken ministry are named for further "
            "study, and readers are warmly encouraged to obtain those works "
            "from their rightful publishers. Scripture quotations are from the "
            "Authorised (King James) Version."
        ),
        cover_color="#7a0a5a",
    ),
    # C. S. Lewis's own works are NOT public domain — and his estate actively
    # protects them. This companion quotes only the KJV and paraphrases; not a
    # sentence of his is reproduced, and the disavowal is essential and must ship.
    "key-teachings-of-c-s-lewis": Work(
        slug="key-teachings-of-c-s-lewis",
        title="The Key Teachings of C. S. Lewis",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="c-s-lewis",
        source="c-s-lewis.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by "
            "the C. S. Lewis estate or any organisation holding rights in the "
            "writings of C. S. Lewis. All descriptions of his teaching are the "
            "present author's own summaries; none of his words are reproduced, "
            "and his books are named for further study, which readers are "
            "warmly encouraged to obtain from their rightful publishers. "
            "Scripture quotations are from the Authorised (King James) Version."
        ),
        cover_color="#2f4a6e",
    ),
    # George MacDonald IS public domain, so — unlike the Lewis volume — he is
    # quoted, briefly, and only in lines checked against the library's own text
    # of Unspoken Sermons (each sermon is named where it is quoted).
    "key-teachings-of-george-macdonald": Work(
        slug="key-teachings-of-george-macdonald",
        title="The Key Teachings of George MacDonald",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="george-macdonald",
        source="george-macdonald.md",  # description + about in its front matter
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. George MacDonald's own words are quoted only briefly, from "
            "the text of his Unspoken Sermons in the Ochorus library; elsewhere "
            "his teaching is set out in modern prose. His writings are in the "
            "public domain and freely available; readers are encouraged to go to "
            "them directly. Scripture quotations are from the Authorised (King "
            "James) Version."
        ),
        cover_color="#24503f",
    ),
}


# A Markdown manuscript — the source of every volume. Its grammar is the shape
# the first volumes' PDF template set, stated rather than inferred:
#
#     ---                         front matter: `description: <one line>` and
#     description: …              `about: |` then indented paragraphs, blank-
#     about: |                    line separated (-> the `about_html` <p>s)
#       First paragraph …
#     ---
#     # Chapter Title             -> a chapter boundary
#     ## A subheading             -> <h2>
#     ### A PRAYER                -> <blockquote>A PRAYER</blockquote>, the
#                                    series' set-apart label
#     > Words. PSALM 73:25        -> one <blockquote> per line (Scripture, or a
#                                    line of the closing prayer)
#     1. An application point     -> its own <p>
#     prose lines                 -> <p>, paragraphs split on a blank line
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_POINT = re.compile(r"^\d+\.\s")


def _front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split ``text`` into its (tiny, two-key) front matter and the body."""
    text = text.replace("\r\n", "\n")
    m = _FRONT.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    key, block = None, False
    for line in m.group(1).splitlines():
        head = re.match(r"^(\w+):\s*(.*)$", line)
        if head and not line.startswith(" "):
            key, value = head.groups()
            block = value == "|"
            meta[key] = "" if block else value.strip()
        elif key and block:  # `|` keeps line breaks: they split paragraphs
            meta[key] += line.strip() + "\n"
        elif key and line.strip():  # a wrapped one-line value folds
            meta[key] = f"{meta[key]} {line.strip()}".strip()
    return meta, text[m.end():]


def _paras_html(block: str) -> str:
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", block) if p.strip()]
    return "".join(f"<p>{html.escape(p, quote=False)}</p>" for p in paras)


def manuscript(text: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Parse a Markdown manuscript into (meta, [(title, body_html), …])."""
    meta, body = _front_matter(text)
    if "about" in meta:
        meta["about_html"] = _paras_html(meta.pop("about"))
    chapters: list[tuple[str, str]] = []
    title: str | None = None
    parts: list[tuple[str, str]] = []
    para: list[str] = []

    def flush_para() -> None:
        if para:
            parts.append(("p", " ".join(para)))
            para.clear()

    def flush_chapter() -> None:
        flush_para()
        if title is None and parts:
            raise CommandError("manuscript: text before the first `# ` chapter heading")
        if title is not None:
            chapters.append((
                recase_title(title),
                "".join(f"<{t}>{html.escape(x, quote=False)}</{t}>" for t, x in parts),
            ))
        parts.clear()

    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            flush_chapter()
            title = line[2:].strip()
        elif not line:
            flush_para()
        elif line.startswith("#") and not line.startswith(("## ", "### ")):
            raise CommandError(f"manuscript: malformed heading {line[:40]!r}")
        elif line.startswith("## "):
            flush_para()
            parts.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            flush_para()
            parts.append(("blockquote", line[4:].strip().upper()))
        elif line.startswith(">"):
            flush_para()
            if line[1:].strip():
                parts.append(("blockquote", line[1:].strip()))
        elif _POINT.match(line):
            flush_para()
            parts.append(("p", line))
        else:
            para.append(line)
    flush_chapter()
    return meta, chapters


class Command(BaseCommand):
    help = "Build the Key Teachings of … study-companion series."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Work slugs (default: all).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        unknown = wanted - set(WORKS)
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for slug, work in WORKS.items():
            if wanted and slug not in wanted:
                continue
            self._build(work)

    @transaction.atomic
    def _build(self, work: Work) -> None:
        self.stdout.write(f"→ {work.title}")
        path = DATA_DIR / work.source
        if not path.exists():
            raise CommandError(f"missing source: {path}")
        subject = Author.objects.get(slug=work.author_slug)  # exists in authors.json
        meta, chapters = manuscript(path.read_text(encoding="utf-8"))
        description = meta.get("description", "")
        about_html = meta.get("about_html", "")
        if not (description and about_html):
            raise CommandError(f"{work.slug}: no description / about — aborted.")
        if len(chapters) < 3:
            raise CommandError(f"{work.slug}: only {len(chapters)} chapters — aborted.")

        content = {
            "author": Author.objects.get(slug="ochorus-originals"),
            "cover_byline": subject.name,
            "title": work.title,
            "subtitle": work.subtitle,
            "description": description,
            "attribution": work.attribution,
            "about_html": about_html,
            "cover_color": work.cover_color,
            # A collection, not a reading order: no volume numeral.
            "series": Series.objects.get(slug="key-teachings"),
            "cover_url": work.cover_url,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=work.slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                # Published — the founder reviewed the render and cleared the
                # series (migration 0155 flipped the rows already on prod).
                # Create-only, so the admin's later toggle is never walked back.
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(work.slug, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 120:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:46]:46} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {work.title!r} — {book.chapter_count} chapters"))
