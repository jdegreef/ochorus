"""Upsert the fixture's articles into an already-seeded database.

``seed_if_empty`` only populates a *fresh* database, so articles added to the
committed fixture never reach an existing production DB on their own. This
command reads that same fixture and upserts every article row — new articles are
created, changed ones are updated, untouched ones are left alone. Runs on every
deploy (see the release command); idempotent, and the fixture stays the single
source of truth.

Follows seed_sermons, with two differences: an Article has **no author**, so
there is no author to create or reconcile; and it has no derived columns, so
``save()`` has nothing to re-derive and a plain field copy is the whole update.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from library.content_fixtures import load_all_rows
from library.management.commands.seed_books import require_natural_format
from library.models import Article

# The fields the fixture owns. No derived columns exist on Article (unlike
# Chapter/Sermon, which derive word_count from body_html), so every field here
# is a plain stored value the fixture may set.
ARTICLE_FIELDS = (
    "h1",
    "meta_title",
    "description",
    "body_html",
    "related",
    "source_url",
    "sort_order",
    "is_published",
)

# Seeded on create, then owned by whoever acts on the live DB: an urgent
# unpublish happens directly in the database, and re-asserting the fixture's
# ``is_published`` on every deploy would silently resurrect a pulled article.
# Same reasoning as seed_sermons.CREATE_ONLY_FIELDS (which also carries
# source_type; articles have none yet — English originals, not translations).
CREATE_ONLY_FIELDS = frozenset({"is_published"})
UPDATE_FIELDS = tuple(f for f in ARTICLE_FIELDS if f not in CREATE_ONLY_FIELDS)


class Command(BaseCommand):
    help = "Upsert the fixture's articles into an existing DB (deploy step)."

    # Atomic like seed_sermons: a mid-loop DB error must not leave prod with a
    # half-synced article set.
    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            rows = load_all_rows()
        except OSError:
            self.stdout.write("No content fixtures available — nothing to seed.")
            return
        # A ValueError (corrupt file, path named) propagates: "one file is
        # broken" must abort the deploy, not skip all content.

        require_natural_format(rows, "seed_articles")

        created = updated = 0
        for row in rows:
            if row.get("model") != "library.article":
                continue
            f = row["fields"]
            language = f.get("language", "en")
            article = Article.objects.filter(
                slug=f["slug"], language=language
            ).first()

            if article is None:
                Article.objects.create(
                    slug=f["slug"],
                    language=language,
                    # Omit fields the fixture row doesn't carry so the model
                    # default applies (e.g. a row predating a field).
                    **{k: f[k] for k in ARTICLE_FIELDS if k in f},
                )
                created += 1
                continue

            changed = [
                k for k in UPDATE_FIELDS if k in f and getattr(article, k) != f[k]
            ]
            if changed:
                for k in changed:
                    setattr(article, k, f[k])
                article.save()
                updated += 1

        if created or updated:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Articles: {created} created, {updated} updated."
                )
            )
        else:
            self.stdout.write("Articles already up to date.")
