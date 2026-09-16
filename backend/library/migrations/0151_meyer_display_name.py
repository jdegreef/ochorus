from django.db import migrations

# F. B. Meyer's author row was created with his full name, "Frederick Brotherton
# Meyer" — 26 characters, which overflows the cover byline and truncates to
# "FREDERICK BROTHERTON M…". He published as "F. B. Meyer", which is also how the
# rest of the library should name him. The fixture (authors.json) now carries the
# short form, but `name` is not among the fields the seeds re-sync onto an
# existing author (see library/author_sync.py: only `same_as` is synced, the rest
# are fill-only), so the live row needs this one-off update to change on deploy.

SLUG = "frederick-brotherton-meyer"
SHORT = "F. B. Meyer"
FULL = "Frederick Brotherton Meyer"


def to_short(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG).update(name=SHORT)


def to_full(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG).update(name=FULL)


class Migration(migrations.Migration):
    dependencies = [("library", "0150_sermon_attribution")]
    operations = [migrations.RunPython(to_short, to_full)]
