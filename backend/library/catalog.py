"""The Ochorus launch shelf: 10 public-domain Christian classics.

`ccel_id` is the work's path under ccel.org/ccel/<ccel_id>. These are best-guess
identifiers verified/corrected against the live site during ingestion. The order
of this list is the shelf order.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthorEntry:
    slug: str
    name: str
    birth_year: int
    death_year: int
    bio: str = ""


@dataclass(frozen=True)
class BookEntry:
    slug: str
    title: str
    author_slug: str
    ccel_id: str
    subtitle: str = ""
    cover_color: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)


AUTHORS: dict[str, AuthorEntry] = {
    "andrew-murray": AuthorEntry(
        slug="andrew-murray",
        name="Andrew Murray",
        birth_year=1828,
        death_year=1917,
        bio=(
            "South African pastor and writer of the Dutch Reformed Church, "
            "known for devotional classics on prayer, humility, and abiding in Christ."
        ),
    ),
    "charles-spurgeon": AuthorEntry(
        slug="charles-spurgeon",
        name="Charles H. Spurgeon",
        birth_year=1834,
        death_year=1892,
        bio=(
            "English Baptist preacher, the “Prince of Preachers,” whose sermons "
            "and devotional writings have been read by millions."
        ),
    ),
}

# Shelf order matters: tiny, clean books first (best first-ingest test cases).
BOOKS: list[BookEntry] = [
    BookEntry("humility", "Humility", "andrew-murray", "murray/humility",
              subtitle="The Beauty of Holiness", cover_color="#3b5bdb"),
    BookEntry("all-of-grace", "All of Grace", "charles-spurgeon", "spurgeon/grace",
              subtitle="An Earnest Word to Those Seeking Salvation", cover_color="#b08900"),
    BookEntry("abide-in-christ", "Abide in Christ", "andrew-murray", "murray/abide",
              cover_color="#2b8a3e"),
    BookEntry("school-of-prayer", "With Christ in the School of Prayer",
              "andrew-murray", "murray/prayer", cover_color="#5f3dc4"),
    BookEntry("absolute-surrender", "Absolute Surrender", "andrew-murray",
              "murray/surrender", cover_color="#c92a2a"),
    BookEntry("waiting-on-god", "Waiting on God", "andrew-murray", "murray/waiting",
              cover_color="#1864ab"),
    BookEntry("inner-chamber", "The Inner Chamber", "andrew-murray",
              "murray/innerchamber", cover_color="#0b7285"),
    BookEntry("according-to-promise", "According to Promise", "charles-spurgeon",
              "spurgeon/promise", cover_color="#a61e4d"),
    BookEntry("johnploughman", "John Ploughman's Talk", "charles-spurgeon",
              "spurgeon/ploughman",
              subtitle="Plain Advice for Plain People", cover_color="#846358"),
    BookEntry("cheque-book", "The Cheque Book of the Bank of Faith",
              "charles-spurgeon", "spurgeon/checkbook",
              subtitle="Daily Readings on God's Promises", cover_color="#2f9e44"),
]
