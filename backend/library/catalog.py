"""The Ochorus launch shelf: 10 public-domain Christian classics.

Each book declares its `source` ("ccel" or "gutenberg") and a `source_ref`:
  - ccel:      the work path under ccel.org/ccel/<ref>  (e.g. "spurgeon/grace")
  - gutenberg: the Project Gutenberg ebook id as a string (e.g. "57121")

The order of BOOKS is the shelf order.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    source: str  # "ccel" | "gutenberg"
    source_ref: str
    subtitle: str = ""
    cover_color: str = ""


AUTHORS: dict[str, AuthorEntry] = {
    "andrew-murray": AuthorEntry(
        slug="andrew-murray",
        name="Andrew Murray",
        birth_year=1828,
        death_year=1917,
        bio=(
            "South African pastor and writer of the Dutch Reformed Church, known "
            "for devotional classics on prayer, humility, and abiding in Christ."
        ),
    ),
    "charles-spurgeon": AuthorEntry(
        slug="charles-spurgeon",
        name="Charles H. Spurgeon",
        birth_year=1834,
        death_year=1892,
        bio=(
            "English Baptist preacher, the “Prince of Preachers,” whose sermons and "
            "devotional writings have been read by millions."
        ),
    ),
    "dwight-l-moody": AuthorEntry(
        slug="dwight-l-moody",
        name="Dwight L. Moody",
        birth_year=1837,
        death_year=1899,
        bio=(
            "American evangelist whose plain, warm gospel addresses reached "
            "millions across America and Britain; founder of the Moody Bible "
            "Institute."
        ),
    ),
}

# Shelf order. Small, clean books first.
BOOKS: list[BookEntry] = [
    BookEntry("humility", "Humility", "andrew-murray", "gutenberg", "57121",
              subtitle="The Beauty of Holiness", cover_color="#3b5bdb"),
    BookEntry("all-of-grace", "All of Grace", "charles-spurgeon", "ccel", "spurgeon/grace",
              subtitle="An Earnest Word to Those Seeking Salvation", cover_color="#b08900"),
    BookEntry("absolute-surrender", "Absolute Surrender", "andrew-murray",
              "ccel", "murray/surrender", cover_color="#c92a2a"),
    BookEntry("school-of-prayer", "With Christ in the School of Prayer",
              "andrew-murray", "ccel", "murray/prayer", cover_color="#5f3dc4"),
    BookEntry("true-vine", "The True Vine", "andrew-murray", "ccel", "murray/true_vine",
              subtitle="Meditations for a Month on John 15", cover_color="#2b8a3e"),
    BookEntry("waiting-on-god", "Waiting on God", "andrew-murray", "ccel", "murray/waiting",
              cover_color="#1864ab"),
    BookEntry("ministry-of-intercession", "The Ministry of Intercession",
              "andrew-murray", "gutenberg", "29296",
              subtitle="A Plea for More Prayer", cover_color="#0b7285"),
    BookEntry("around-the-wicket-gate", "Around the Wicket Gate", "charles-spurgeon",
              "gutenberg", "60669",
              subtitle="A Friendly Talk with Seekers", cover_color="#a61e4d"),
    BookEntry("talks-to-farmers", "Talks to Farmers", "charles-spurgeon",
              "gutenberg", "42518",
              subtitle="Plain Advice in Parables", cover_color="#846358"),
    BookEntry("cheque-book", "The Cheque Book of the Bank of Faith",
              "charles-spurgeon", "ccel", "spurgeon/checkbook",
              subtitle="Daily Readings on God's Promises", cover_color="#2f9e44"),
    BookEntry("till-he-come", "Till He Come",
              "charles-spurgeon", "ccel", "spurgeon/till_he_come",
              subtitle="Communion Meditations and Addresses", cover_color="#704881"),
    BookEntry("the-way-to-god", "The Way to God", "dwight-l-moody",
              "gutenberg", "30449",
              subtitle="And How to Find It", cover_color="#9a3412"),
    BookEntry("prevailing-prayer", "Prevailing Prayer", "dwight-l-moody",
              "gutenberg", "61883",
              subtitle="What Hinders It?", cover_color="#365314"),
]
