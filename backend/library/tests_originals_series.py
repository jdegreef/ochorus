"""The house's single-subject series are BY the imprint and ABOUT one person.

A Portraits of Courage life or a Key Teachings companion was once filed under
the person it is about, which credited Watchman Nee with his own biography — in
the byline, on his author page, and as schema.org ``author``. Now each volume is
by ``ochorus-originals``, and the person is kept in two places that must agree:
``cover_byline`` (the name the cover sets across its top, on every language row)
and a ``BOOK_PEOPLE`` entry naming them the book's lone subject (what files it
under "Books about" on their author page). A new volume that misses either
fails here, before it ships a cover reading "Ochorus Originals" or drops off its
subject's page.
"""

from django.test import SimpleTestCase

from .book_people_seed import BOOK_PEOPLE
from .content_fixtures import authors_by_slug, book_editions

#: The series whose every volume is about exactly one person.
SINGLE_SUBJECT_SERIES = ("key-teachings", "portraits-of-courage")
IMPRINT = "ochorus-originals"


class SingleSubjectSeriesTests(SimpleTestCase):
    def test_every_volume_is_by_the_imprint_and_about_its_lone_subject(self):
        authors = authors_by_slug()
        people = dict(BOOK_PEOPLE)
        seen = 0
        for path, slug, _language, fields in book_editions():
            if (fields.get("series") or [None])[0] not in SINGLE_SUBJECT_SERIES:
                continue
            seen += 1
            where = path.name
            self.assertEqual(fields["author"], [IMPRINT], f"{where}: not by the imprint")
            subjects = [p for p, role, *_ in people.get(slug, []) if role == "subject"]
            self.assertEqual(
                len(subjects), 1,
                f"{where}: BOOK_PEOPLE must name exactly one subject for {slug}",
            )
            self.assertEqual(
                fields.get("cover_byline"), authors[subjects[0]]["name"],
                f"{where}: cover_byline must be {subjects[0]}'s name",
            )
        self.assertGreater(seen, 0, "no volumes found — did a series slug change?")
