"""The starter templates every admin can begin an email from.

Kept in code, not the database, so an improvement to one ships with a deploy and
every environment has the same set; a team's own templates are
:class:`~emails.models.EmailTemplate` rows beside them. Each is written in
English — "Draft with AI" adds the other languages to the broadcast made from
it — out of the same blocks the designer edits, so nothing in one is locked.

Words the admin is meant to replace are written ``[Like this]`` — a capitalised
hint in square brackets — and the pre-send checks refuse to send an email that
still has one (``preflight.PLACEHOLDER``), so a starter can't go out unedited.
The library blocks name works the library has in many languages; swap them for
the month's own picks.
"""

from __future__ import annotations

from .models import TemplateCategory as C


def _letter_close() -> dict:
    return {"type": "text", "text": "Grace and peace,\nThe Ochorus team"}


def _book(slug: str, label: str = "") -> dict:
    return {"type": "book", "slug": slug, "label": label}


STARTERS: list[dict] = [
    {
        "key": "monthly-newsletter",
        "name": "Monthly newsletter",
        "category": C.NEWSLETTER,
        "description": "A short letter, three books, a quote and a plan to start.",
        "subject": "[This month at Ochorus]",
        "preheader": "New classics, a line worth keeping, and a plan for the month.",
        "blocks": [
            {"type": "heading", "text": "[This month at Ochorus]"},
            {"type": "text", "text": "Dear {name},\n\n[A few sentences about the month — what was added, and why it matters.]"},
            {"type": "heading", "text": "New in the library"},
            _book("the-pursuit-of-god", "Start reading"),
            _book("absolute-surrender", "Start reading"),
            _book("power-through-prayer", "Start reading"),
            {"type": "divider"},
            {
                "type": "quote",
                "text": "Humility is the only soil in which the graces root.",
                "attribution": "Andrew Murray, Humility",
            },
            {"type": "heading", "text": "A plan to start"},
            {"type": "plan", "slug": "humility-12-days", "label": "Begin day one"},
            {"type": "button", "label": "Explore the library", "path": "books"},
            _letter_close(),
        ],
    },
    {
        "key": "new-book",
        "name": "New book",
        "category": C.ANNOUNCEMENT,
        "description": "One book, front and centre, with a word on why to read it.",
        "subject": "Now in the library: [Book title]",
        "preheader": "A classic, newly added — free to read today.",
        "blocks": [
            {"type": "heading", "text": "Now in the library"},
            _book("the-practice-of-the-presence-of-god"),
            {"type": "text", "text": "[Why this book, and who it is for — two or three sentences.]"},
            {"type": "button", "label": "Browse the library", "path": "books"},
            _letter_close(),
        ],
    },
    {
        "key": "author-spotlight",
        "name": "Author spotlight",
        "category": C.NEWSLETTER,
        "description": "A short life, a pull-quote, and books by one author.",
        "subject": "Meet [Author name]",
        "preheader": "A life worth knowing, and where to start reading.",
        "blocks": [
            {"type": "heading", "text": "[Author name]"},
            {"type": "text", "text": "[A paragraph on their life — where they served, what they are remembered for.]"},
            {"type": "quote", "text": "[A line of theirs]", "attribution": "[Author name], [Book]"},
            {"type": "heading", "text": "Where to start"},
            _book("absolute-surrender"),
            _book("humility-2"),
            {"type": "button", "label": "Read their story", "path": "biographies"},
            _letter_close(),
        ],
    },
    {
        "key": "plan-launch",
        "name": "Reading plan launch",
        "category": C.ANNOUNCEMENT,
        "description": "Introduce a reading plan and invite readers to day one.",
        "subject": "A new reading plan: [Plan name]",
        "preheader": "A chapter a day — begin whenever you are ready.",
        "blocks": [
            {"type": "heading", "text": "[Plan name]"},
            {"type": "text", "text": "Dear {name},\n\n[What the plan covers, how long it takes, and who it is for.]"},
            {"type": "plan", "slug": "humility-12-days", "label": "Begin day one"},
            {"type": "button", "label": "See all reading plans", "path": "plans"},
            _letter_close(),
        ],
    },
    {
        "key": "seasonal-devotional",
        "name": "Seasonal devotional",
        "category": C.SEASONAL,
        "description": "For Advent, Lent, Easter or the new year: a Scripture, a reflection, a plan.",
        "subject": "[An Advent reading]",
        "preheader": "A few quiet minutes for the season.",
        "blocks": [
            {"type": "heading", "text": "[An Advent reading]"},
            {"type": "quote", "text": "[A verse for the season]", "attribution": "[Reference]"},
            {"type": "text", "text": "[A short reflection — a paragraph or two from a classic, or your own words.]"},
            {"type": "plan", "slug": "humility-12-days", "label": "Read through the season"},
            _letter_close(),
        ],
    },
    {
        "key": "book-recommendation",
        "name": "Book recommendation",
        "category": C.NEWSLETTER,
        "description": "Personal: the book each reader is in the middle of, and one to read next.",
        "subject": "One to read next",
        "preheader": "Picked for you from the library.",
        "blocks": [
            {"type": "heading", "text": "You might love this"},
            {"type": "continue_reading", "heading": "Where you left off", "label": "Pick up at chapter {chapter}"},
            {"type": "text", "text": "[Why the next book follows on from what they are reading.]"},
            _book("humility-2", "Start reading"),
            _letter_close(),
        ],
    },
    {
        "key": "simple-letter",
        "name": "Simple letter",
        "category": C.OTHER,
        "description": "Just words and a signature — for a personal note or an update.",
        "subject": "[Subject]",
        "preheader": "",
        "blocks": [
            {"type": "text", "text": "Dear {name},\n\n[Your note.]"},
            _letter_close(),
        ],
    },
]


def serialize(starter: dict) -> dict:
    """A starter in the same shape as a saved template, keyed by ``key``."""
    return {
        "key": starter["key"],
        "name": starter["name"],
        "category": starter["category"],
        "description": starter["description"],
        "subject": {"en": starter["subject"]},
        "content": {"en": {"preheader": starter["preheader"], "blocks": starter["blocks"]}},
        "locales": ["en"],
    }
