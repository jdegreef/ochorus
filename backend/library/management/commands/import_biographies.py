"""Scrape author biographies from ochorus.com/author-biographies/ into Author.bio.

Matches each scraped writer to an existing Author by (first name, surname); when
there's no match (e.g. a writer with no book in the catalogue), a bio-only Author
is created so the Biographies page mirrors ochorus.com.

    python manage.py import_biographies
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from library.models import Author

URL = "https://ochorus.com/author-biographies/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_PERSON = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z.]+){1,3}$")


def _key(name: str) -> tuple[str, str]:
    toks = name.replace(".", "").split()
    return (toks[0].lower(), toks[-1].lower()) if toks else ("", "")


def scrape() -> list[tuple[str, str]]:
    html = requests.get(URL, headers={"User-Agent": UA}, timeout=60).text
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for h in soup.select("h1,h2,h3,h4,h5"):
        name = h.get_text(" ", strip=True)
        if not _PERSON.match(name) or name in seen:
            continue
        p = h.find_next("p")
        bio = p.get_text(" ", strip=True) if p else ""
        if len(bio) < 60:
            continue
        # A real bio opens with the writer's name; this filters section headings
        # like "Find Your Christian Writers" whose following text is someone else's bio.
        first, last = name.split()[0].lower(), name.split()[-1].lower()
        if first not in bio[:40].lower() and last not in bio[:40].lower():
            continue
        seen.add(name)
        out.append((name, bio))
    return out


class Command(BaseCommand):
    help = "Import author biographies from ochorus.com."

    def handle(self, *args, **opts):
        existing = {_key(a.name): a for a in Author.objects.all()}
        bios = scrape()
        updated = created = 0
        for name, bio in bios:
            author = existing.get(_key(name))
            if author:
                author.bio = bio
                author.save(update_fields=["bio"])
                updated += 1
            else:
                Author.objects.create(slug=slugify(name)[:120], name=name, bio=bio)
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f"Biographies: {updated} updated, {created} created.")
        )
