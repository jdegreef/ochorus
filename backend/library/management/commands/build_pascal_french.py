"""Build Pascal's works in French — the originals, not translations.

Every other non-English book in the library is an AI translation of an English
edition (``ai_unreviewed`` until approved). These are Pascal's own French, so
they are ``public_domain`` — the source type the model defines as "Public domain
(original language)" — and carry no review badge. Three works:

* ``pensees`` (fr) — Brunschvicg's text (Hachette, *Œuvres de Blaise Pascal*,
  1904–1921) from French Wikisource, section by section. The fourteen sections
  are the fourteen chapters, matching the English (Trotter translated the same
  arrangement). Each fragment keeps the number this edition gives it; that
  numbering runs close to, but not exactly with, Trotter's, and some fragments
  are ``bis``. The manuscript reference printed before each number is dropped.
* ``provincial-letters`` (fr) — *Les Provinciales* in Pierre de la Vallée's 1657
  collected edition, as transcribed on French Wikisource (letters 1–18 and the
  Provincial's reply, folded into letter 2 as in the English). That edition
  predates the nineteenth letter, a fragment published after Pascal's death;
  its text is taken from the 1875 Charpentier edition (Internet Archive
  ``lesprovincialesod00mpasc``), checked by hand and committed under
  ``data/les-provinciales/``. Chapter titles are the lead clause of each
  letter's printed argument (from the 1875 edition).
* ``life-of-pascal`` (fr only) — Gilberte Périer's *Vie de Blaise Pascal*, from
  the 1871 Hachette *Œuvres complètes* on French Wikisource, in its period
  spelling. The source has no divisions; it is set in four parts at the turns
  of the narrative.

Fixture-driven like every other book: ``seed_books`` creates the rows on the
next deploy. This command GENERATES the three fixtures reproducibly.

    DJANGO_DEBUG=true uv run python manage.py build_pascal_french
"""

from __future__ import annotations

import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, wikisource
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import convert_work

HOST = "fr.wikisource.org"
LANGUAGE = "fr"
AUTHOR_SLUG = "blaise-pascal"
AUTHOR_STUB = {"name": "Blaise Pascal", "birth_year": 1623, "death_year": 1662}
DATA = Path(__file__).resolve().parent / "data" / "les-provinciales"

# French sets its apostrophe curly, like every French edition in the library.
_APOSTROPHE = re.compile(r"(?<=\w)'(?=\w)")


def _french(html: str) -> str:
    """House typography for a French body: curly apostrophes, no long s."""
    return _APOSTROPHE.sub("’", html).replace("ſ", "s")


# ── Pensées ──────────────────────────────────────────────────────────────────

PENSEES_ROOT = "Pensées (Pascal, éd. Brunschvicg)/Pensées/Section "
# (title, the Wikisource pages that make the section)
PENSEES_SECTIONS = [
    ("Pensées sur l’esprit et sur le style", ["I"]),
    ("Misère de l’homme sans Dieu", ["II-1", "II-2"]),
    ("De la nécessité du pari", ["III"]),
    ("Des moyens de croire", ["IV"]),
    ("La justice et la raison des effets", ["V"]),
    ("Les philosophes", ["VI"]),
    ("La morale et la doctrine", ["VII"]),
    ("Les fondements de la religion chrétienne", ["VIII"]),
    ("La perpétuité", ["IX"]),
    ("Les figuratifs", ["X"]),
    ("Les prophéties", ["XI"]),
    ("Preuves de Jésus-Christ", ["XII"]),
    ("Les miracles", ["XIII"]),
    ("Fragments polémiques", ["XIV"]),
]
# "Première Copie 226] 559 bis" → "559 bis": a fragment's number, after the
# manuscript reference.
_FRAGMENT = re.compile(r"(?:^|\]\s*)(\d+(?: bis| ter)?)\s*$")
# One heading on the section I page reads "10" where the fragment is 54 (it sits
# between 53 and 55, and 10 is already set earlier in the section).
PENSEES_RENUMBER = {("I", "*201] 10", 2): "54"}
EXPECTED_PENSEES_FRAGMENTS = 983


def _pensees() -> list[tuple[str, str]]:
    chapters = []
    total = 0
    for title, pages in PENSEES_SECTIONS:
        parts: list[str] = []
        for page in pages:
            seen: dict[str, int] = {}
            for b in wikisource.blocks(wikisource.fetch(HOST, PENSEES_ROOT + page)):
                if b.kind == "heading":
                    if b.text.startswith("SECTION"):
                        continue
                    m = _FRAGMENT.search(b.text)
                    if not m:
                        continue  # an editor's note label, e.g. "(1)"
                    seen[b.text] = seen.get(b.text, 0) + 1
                    number = PENSEES_RENUMBER.get((page, b.text, seen[b.text]), m.group(1))
                    parts.append(f"<h3>{number}</h3>")
                    total += 1
                elif b.kind in ("p", "center", "right"):
                    if not parts:
                        raise CommandError(f"Pensées {page}: text before the first fragment.")
                    parts.append(f"<p>{b.html}</p>")
        chapters.append((title, "".join(parts)))
    if total != EXPECTED_PENSEES_FRAGMENTS:
        raise CommandError(f"expected {EXPECTED_PENSEES_FRAGMENTS} fragments, found {total}.")
    return chapters


# ── Les Provinciales ─────────────────────────────────────────────────────────

VALLEE = "Les Provinciales (Vallée)/"
PROVINCIALES_TITLES = [
    "Des disputes de Sorbonne et de l’invention du pouvoir prochain",
    "De la grâce suffisante",
    "Injustice, absurdité et nullité de la censure de M. Arnauld",
    "De la grâce actuelle et des péchés d’ignorance",
    "Dessein des jésuites en établissant une nouvelle morale",
    "Différents artifices des jésuites pour éluder l’autorité de l’Évangile",
    "De la méthode de diriger l’intention",
    "Maximes corrompues des casuistes touchant les juges et les usuriers",
    "De la fausse dévotion à la sainte Vierge",
    "Adoucissements apportés au sacrement de pénitence",
    "Qu’on peut réfuter par des railleries les erreurs ridicules",
    "Réfutation des chicanes des jésuites sur l’aumône et la simonie",
    "Combien il est facile de passer de la spéculation à la pratique",
    "Les maximes des jésuites sur l’homicide réfutées par les Pères",
    "Que les jésuites ôtent la calomnie du nombre des crimes",
    "Calomnies horribles contre de pieux ecclésiastiques et de saintes religieuses",
    "L’équivoque du sens de Jansénius",
    "Qu’il n’y a aucune hérésie dans l’Église",
    "Fragment d’une dix-neuvième lettre, au père Annat",
]
REPLY_TITLE = "Réponse du provincial aux deux premières lettres de son ami"
# Letter 1 keeps the 1657 typography in its opening line, where the rest of the
# transcription is modernised; the head is set like its siblings.
PROVINCIALES_FIXES = [("M<strong>ONSIEVR</strong>, Nous eſtions", "Monsieur, Nous étions")]

_DATELINE = re.compile(r"^(?:(?:De Paris|Du|Le|Ce)\b[^.]{0,40}|\d{1,2}\S* \w+ )1[56]\d\d\b")
_SALUTATION = re.compile(r"^(?:Monsieur|Mes Révérends Pères|Mon Révérend Père)\b", re.I)


def _letter(page: str) -> list[str]:
    """One Vallée page: its title lines dropped, its dateline kept in italics."""
    blocks = wikisource.blocks(wikisource.fetch(HOST, VALLEE + page))
    html = [b.html for b in blocks]
    for bad, good in PROVINCIALES_FIXES:
        html = [h.replace(bad, good) for h in html]
    start = next(
        (i for i, h in enumerate(html) if _DATELINE.match(_text(h)) or _SALUTATION.match(_text(h))),
        None,
    )
    if start is None:
        raise CommandError(f"Provinciales {page}: no dateline or salutation found.")
    body = html[start:]
    # A trailing heading of the NEXT letter ("Troisième lettre pour servir…").
    if re.match(r"^\S+ lettre\b", _text(body[-1]), re.I) and not re.search(r"[.!?»]$", _text(body[-1])):
        body = body[:-1]
    out = []
    for h in body:
        out.append(f"<p><em>{_text(h)}</em></p>" if _DATELINE.match(_text(h)) else f"<p>{h}</p>")
    return out


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _provinciales() -> list[tuple[str, str]]:
    chapters = []
    for n, title in enumerate(PROVINCIALES_TITLES, start=1):
        if n == 19:
            body = (DATA / "lettre-19.html").read_text(encoding="utf-8")
        else:
            parts = _letter(str(n))
            if n == 2:
                parts += [f"<h3>{REPLY_TITLE}</h3>", *_letter("2r")]
            body = "".join(parts)
        chapters.append((title, body))
    return chapters


# ── Vie de Blaise Pascal ─────────────────────────────────────────────────────

VIE_PAGE = "Œuvres complètes de Blaise Pascal (Hachette, 1871)/Vie de Blaise Pascal"
# (title, first block, block after the last); the source's two title lines
# (blocks 0–1) are the book's title, not text.
VIE_PARTS = [
    ("Son enfance et ses premiers travaux", 2, 17),
    ("Sa conversion et sa retraite", 17, 34),
    ("Ses maux et ses vertus", 34, 53),
    ("Sa dernière maladie et sa mort", 53, 60),
]
# The first block of each part, so a re-flowed source fails loudly instead of
# splitting mid-thought.
VIE_OPENINGS = ["Mon frère naquit à Clermont", "Immédiatement après cette expérience",
                "Ce renouvellement de ses maux", "Elle commença par un dégoût"]


def _vie() -> list[tuple[str, str]]:
    blocks = wikisource.blocks(wikisource.fetch(HOST, VIE_PAGE))
    if len(blocks) != VIE_PARTS[-1][2]:
        raise CommandError(f"Vie: expected {VIE_PARTS[-1][2]} blocks, found {len(blocks)}.")
    chapters = []
    for (title, lo, hi), opening in zip(VIE_PARTS, VIE_OPENINGS, strict=True):
        if not blocks[lo].text.startswith(opening):
            raise CommandError(f"Vie: part {title!r} no longer opens with {opening!r}.")
        chapters.append((title, "".join(f"<p>{b.html}</p>" for b in blocks[lo:hi])))
    return chapters


# ── the books ────────────────────────────────────────────────────────────────

BOOKS = {
    "pensees": {
        "build": _pensees,
        "title": "Pensées",
        "subtitle": "Texte établi par Léon Brunschvicg",
        "publication_year": 1670,
        "cover_color": "#3b4a5c",
        "source_url": "https://fr.wikisource.org/wiki/Pens%C3%A9es_(Pascal,_%C3%A9d._Brunschvicg)",
        "min_words": 1500,
        "description": (
            "Quand Pascal mourut en 1662, à trente-neuf ans, il laissait des centaines "
            "de notes pour une grande apologie de la religion chrétienne qu’il n’acheva "
            "jamais. Ses amis de Port-Royal les publièrent en 1670 sous le titre de "
            "Pensées. Pascal ne commence pas par les preuves tirées de la nature, mais "
            "par l’homme : sa grandeur et sa misère, son inquiétude, le divertissement "
            "par lequel il fuit la seule question qui compte. On y trouve le roseau "
            "pensant, le pari, « le cœur a ses raisons que la raison ne connaît point », "
            "et le « Mystère de Jésus »."
        ),
        "attribution": (
            "Domaine public — Blaise Pascal, Pensées (1670), texte établi par Léon "
            "Brunschvicg (Œuvres de Blaise Pascal, Hachette) ; texte de Wikisource. Les "
            "quatorze sections forment les chapitres et chaque fragment garde son numéro ; "
            "les notes de l’éditeur ne sont pas reprises."
        ),
    },
    "provincial-letters": {
        "build": _provinciales,
        "title": "Les Provinciales",
        "subtitle": "Lettres écrites par Louis de Montalte à un provincial de ses amis",
        "publication_year": 1657,
        "cover_color": "#5a3e36",
        "source_url": "https://fr.wikisource.org/wiki/Les_Provinciales_(Vall%C3%A9e)",
        "min_words": 300,
        "description": (
            "En janvier 1656, la Sorbonne s’apprêtait à condamner Antoine Arnauld, l’ami "
            "de Pascal à Port-Royal. Pascal prit sa défense dans une lettre anonyme « à un "
            "provincial de ses amis ». Dix-sept autres suivirent en quatorze mois, passées "
            "de main en main dans Paris tandis que la police cherchait les imprimeurs. "
            "Elles commencent en comédie et deviennent une attaque sérieuse et ardente "
            "contre une morale qui avait appris à tout excuser. Elles ont fixé la prose "
            "française moderne."
        ),
        "attribution": (
            "Domaine public — Blaise Pascal, Les Provinciales (1656-1657), dans l’édition "
            "collective de Pierre de la Vallée (1657) transcrite sur Wikisource ; le "
            "fragment de la dix-neuvième lettre, publié après la mort de Pascal, d’après "
            "l’édition Charpentier (1875). La réponse du provincial suit la deuxième lettre."
        ),
    },
    "life-of-pascal": {
        "build": _vie,
        "title": "Vie de Blaise Pascal",
        "subtitle": "Par Mme Périer, sa sœur",
        "publication_year": 1684,
        "cover_color": "#4a4033",
        "source_url": "https://fr.wikisource.org/wiki/%C5%92uvres_compl%C3%A8tes_de_Blaise_Pascal_(Hachette,_1871)/Vie_de_Blaise_Pascal",
        "min_words": 1500,
        "description": (
            "Gilberte Périer, sœur aînée de Pascal, écrivit cette vie peu après sa mort. "
            "Elle raconte l’enfant qui retrouva seul la géométrie d’Euclide, l’inventeur de "
            "la machine arithmétique, puis la conversion de la famille à Rouen et la "
            "retraite de son frère ; elle s’attarde sur son amour de la pauvreté, sa "
            "charité envers les pauvres, sa patience dans la maladie, et sur les derniers "
            "jours où il demandait qu’on fît venir chez lui un pauvre malade pour mourir "
            "en sa compagnie."
        ),
        "attribution": (
            "Domaine public — Gilberte Périer, Vie de Blaise Pascal (publiée en 1684), "
            "d’après les Œuvres complètes de Blaise Pascal (Hachette, 1871) ; texte de "
            "Wikisource, dans son orthographe d’époque. Les quatre parties sont de "
            "l’éditeur d’Ochorus."
        ),
    },
}


class Command(BaseCommand):
    help = "Build Pascal's French originals (Pensées, Provinciales, Vie) in the dev DB."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help=f"any of {', '.join(BOOKS)}; default all")

    @transaction.atomic
    def handle(self, *args, slugs, **opts):
        if unknown := set(slugs) - set(BOOKS):
            raise CommandError(f"unknown slug(s): {sorted(unknown)}")
        author, _ = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        for slug in slugs or BOOKS:
            self._build(author, slug, BOOKS[slug])

    def _build(self, author, slug, spec):
        chapters = spec["build"]()
        bodies, _ = convert_work([_french(b) for _, b in chapters], f"{slug}.fr")
        content = {
            "author": author,
            "title": spec["title"],
            "subtitle": spec["subtitle"],
            "description": spec["description"],
            "attribution": spec["attribution"],
            "publication_year": spec["publication_year"],
            "cover_color": covers.ink_safe(spec["cover_color"]),
            "source_url": spec["source_url"],
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
            language=LANGUAGE,
            defaults=content,
            create_defaults={
                **content,
                # Pascal's own French: the original, not a translation.
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(slug),
            },
        )
        book.chapters.all().delete()
        total = 0
        for order, ((title, _), body) in enumerate(zip(chapters, bodies, strict=True), start=1):
            body = settled_chapter_body(slug, order, clean_fragment(body))
            wc = word_count(body)
            if wc < spec["min_words"]:
                raise CommandError(f"{slug} ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  {slug} ch {order:2}: {title[:56]:56} {wc:>6} words")
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {slug}.fr — {book.chapter_count} chapters, {total} words"))
