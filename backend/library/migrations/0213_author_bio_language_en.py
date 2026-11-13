"""Put 21 authors' ``original_language`` back to "en", the language of their bio.

``Author.original_language`` is the language the base ``bio`` / ``bio_html`` /
``tagline`` are WRITTEN in (``Author._localized`` serves them only to a reader
in that language, and looks for an AuthorTranslation everywhere else). Every
bio in the fixture is English. In November 2026 a translation session's
serialized authors.json carried the authors' native tongues instead — Latin
for Boethius, Jerome, Tertullian, Lactantius and Minucius Felix; Greek for
thirteen Fathers; French, Italian and Spanish for Francis de Sales, Catherine of
Siena and Ignatius of Loyola — and the live rows took the same values. So an
English reader got an empty bio and no tagline for all 21, their pages
advertised a bio in a language nobody wrote one in, and a French reader would
have been handed Francis de Sales's English bio as if it were French.

``seed_books`` / ``seed_sermons`` set ``original_language`` only when they
create an author, so the fixture fix alone never reaches the live rows; this
does. The fixture carries the same fact (a fresh DB loads it after migrate).
Idempotent; irreversible by design (the old values were a mistake).
"""

from __future__ import annotations

from django.db import migrations

SLUGS = (
    "basil-of-caesarea", "boethius", "catherine-of-siena", "clement-of-alexandria",
    "cyril-of-jerusalem", "eusebius-of-caesarea", "francis-de-sales",
    "gregory-of-nazianzus", "gregory-of-nyssa", "hermas", "hippolytus-of-rome",
    "ignatius-of-loyola", "irenaeus-of-lyons", "jerome", "justin-martyr",
    "lactantius", "minucius-felix", "origen-of-alexandria", "polycarp",
    "tertullian", "theophilus-of-antioch",
)


def to_english(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=SLUGS).exclude(original_language="en").update(original_language="en")


class Migration(migrations.Migration):
    dependencies = [("library", "0212_planday_chapter_count")]

    operations = [migrations.RunPython(to_english, migrations.RunPython.noop)]
