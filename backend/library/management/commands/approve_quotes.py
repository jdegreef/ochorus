"""Publish curated quotations — the human gate on the quote pages.

Extraction is mechanical plus judgement; neither is a person deciding a sentence
may be printed under an author's name and shared as a card. So quotations seed
unreviewed and no reader sees one until this command runs, exactly as an AI
translation waits for `approve_translation`.

    manage.py approve_quotes charles-h-spurgeon           # the whole author
    manage.py approve_quotes charles-h-spurgeon --slug X  # one at a time
    manage.py approve_quotes charles-h-spurgeon --list    # read them first

`--list` exists because approving unread is the failure this gate is for.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from library.models import Quote


class Command(BaseCommand):
    help = "Mark an author's curated quotations as reviewed (they then publish)."

    def add_arguments(self, parser):
        parser.add_argument("author", help="Author slug.")
        parser.add_argument("--slug", action="append", help="Approve only these.")
        parser.add_argument("--list", action="store_true", help="Print, approve nothing.")

    def handle(self, *args, **opts):
        qs = Quote.objects.filter(author__slug=opts["author"]).select_related(
            "chapter__book", "sermon"
        )
        if opts["slug"]:
            qs = qs.filter(slug__in=opts["slug"])
        if not qs.exists():
            raise CommandError(f"No quotes for author {opts['author']!r}.")

        if opts["list"]:
            for q in qs:
                mark = "✓" if q.reviewed else " "
                self.stdout.write(f"[{mark}] {q.slug}  {self._cite(q)}\n    {q.text}")
            self.stdout.write(f"\n{qs.filter(reviewed=True).count()}/{qs.count()} reviewed.")
            return

        n = qs.filter(reviewed=False).update(reviewed=True)
        self.stdout.write(self.style.SUCCESS(f"Approved {n} quote(s) for {opts['author']}."))

    def _cite(self, q):
        if q.sermon_id:
            return f"{q.sermon.title} ¶{q.paragraph}"
        return f"{q.chapter.book.title} ch{q.chapter.order} ¶{q.paragraph}"
