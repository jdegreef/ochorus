"""Report quotations whose cited reference does not match what they quote.

    manage.py audit_citations                  # whole English corpus
    manage.py audit_citations the-way-to-god   # one work
    manage.py audit_citations --min-rival 0.75 # tighter, fewer, surer

Deliberately a REPORT, not a check in `english_audit`, and deliberately not
ratcheted. Everything else that module scans is decidable from the text alone —
`L ORD` is wrong whatever the author meant. A citation is not: the verse text
we compare against is the ASV, and these books quote the KJV, so where the two
rest on different manuscripts a KJV clause is simply absent from the ASV at the
cited verse and this reports a mismatch that isn't one. Acts 9:5 is the
standing example.

At the default thresholds it flags 123 of the corpus's ~5,100 quote-citation
pairs. A meaningful minority of those are the ASV/KJV artifact above, and a few
more are the regex pairing a quotation with a reference that belongs to the
sentence after it. So the output is a worklist for a human, and folding it into
the ratchet would assert a precision it has not earned — see
`tests_citations.KnownLimitationTests`.

Two changes moved that number, in opposite directions, and the second is the
more important:

* widening the rival search across books (see `scripture.misattributed`) added
  recall this check never had — every confirmed misattribution in
  `talks-to-the-farmer` names the wrong BOOK;
* reading reference-FIRST citations (LEAD below) removed a large false-positive
  class that predated both changes. `PAIR` alone reads that layout off by one,
  pairing each quotation with the NEXT entry's reference.

Net: 4,397 pairs / 101 findings before, 5,075 pairs / 123 after. The pair count
rose 15% because reference-first entries were not being read at all; the finding
count barely moved because the recall gained and the phantoms lost roughly
cancelled. `religious-affections` alone went from 72 findings to 16.

Worth running before a work goes into the translation queue. This is the one
English defect class that survives translation intact: a translator reproduces
a printed reference faithfully, so one wrong citation becomes one per language.
"""

from __future__ import annotations

import html
import re

from django.core.management.base import BaseCommand

from library import scripture
from library.english_audit import _fixture_records

# A quotation followed by its reference. Loose on purpose — `misattributed`
# rejects anything that isn't a real reference, so a wide net costs nothing
# here, and pythonbible parses the Roman numerals these books set chapters in
# ("Luke xvii. 10") without help.
PAIR = re.compile(
    r"[“\"]([^”\"]{12,700})[”\"][\s,.—-]*\(?\s*"
    r"((?:[1-3]\s+)?[A-Z][A-Za-z]{1,11}\.?\s+[ivxlcIVXLC\d]+[.:]\s*\d+"
    # Ranges AND comma lists — "Matt. 7:13,14", "Rom. iii. 10, 23". Truncating
    # at the first verse hands `misattributed` a citation narrower than the one
    # the book printed, and a quotation of the second verse then reads as a
    # misprint. This regex was the reason the comma fix in scripture.py changed
    # nothing on its own.
    r"(?:\s*[-–—,]\s*\d+)*)\s*\.?\)?"
)
TAG = re.compile(r"<[^>]+>")

# The OTHER layout: reference FIRST, then the quotation. `PAIR` alone reads these
# off by one — it takes each quotation and pairs it with the NEXT entry's
# reference — and that was most of what the sweep reported in the two places it
# reported most:
#
#   Joel 2:28–29 — “Your sons and daughters will prophesy…”      (dash)
#   Rom. 12:11, “Be ye fervent in spirit, serving the Lord.”     (comma)
#
# The first is every Scripture Appendix in the Ochorus Originals; the second is
# how Edwards writes, and he stacks three or four citations a sentence. Together
# they accounted for ~120 phantom findings whose quotations the books had cited
# correctly all along.
#
# The separator may be a dash, a comma or a colon — but NOT a full stop, which
# would swallow the ordinary "…quote” (John 3:16). “Next quote…" shape and
# reintroduce the same off-by-one from the other side.
LEAD = re.compile(
    r"((?:[1-3]\s+)?[A-Z][A-Za-z]{1,11}\.?\s+[ivxlcIVXLC\d]+[.:]\s*\d+"
    r"(?:\s*[-–—,]\s*\d+)*)\s*[—–,:-]\s*[“\"]([^”\"]{12,700})[”\"]"
)


class Command(BaseCommand):
    help = "Report quotations whose cited reference doesn't match the text."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Limit to these works.")
        parser.add_argument(
            "--min-rival",
            type=float,
            default=scripture.RIVAL_MIN,
            help=f"How well a rival verse must fit (default {scripture.RIVAL_MIN}).",
        )

    def handle(self, *args, **opts):
        scripture.RIVAL_MIN = opts["min_rival"]
        wanted = set(opts["slugs"])

        pairs = 0
        by_work: dict[str, list[tuple[str, str, str, str]]] = {}
        for rec in _fixture_records():
            if wanted and rec.work not in wanted:
                continue
            text = html.unescape(TAG.sub(" ", rec.body_html or ""))

            # Reference-first entries are read on their own terms, and their
            # quotation spans are then withheld from PAIR — otherwise the same
            # quotation is scored twice, once against its own reference and once
            # against the next entry's.
            found: list[tuple[str, str]] = []
            claimed: list[tuple[int, int]] = []
            for m in LEAD.finditer(text):
                found.append((m.group(2).strip(), m.group(1).strip()))
                claimed.append((m.start(2), m.end(2)))

            for m in PAIR.finditer(text):
                qs, qe = m.start(1), m.end(1)
                if any(qs < ce and cs < qe for cs, ce in claimed):
                    continue
                found.append((m.group(1).strip(), m.group(2).strip()))

            for quote, ref in found:
                pairs += 1
                try:
                    better = scripture.misattributed(quote, ref)
                except Exception:
                    continue
                if better:
                    by_work.setdefault(rec.work, []).append(
                        (rec.where, ref, better, " ".join(quote.split())[:100])
                    )

        for work in sorted(by_work):
            self.stdout.write(self.style.WARNING(f"\n{work}"))
            for where, ref, better, quote in by_work[work]:
                self.stdout.write(f"  {where}: cites {ref} — reads like {better}")
                self.stdout.write(f"      “{quote}…")

        flagged = sum(len(v) for v in by_work.values())
        self.stdout.write(
            f"\n{pairs} quote+citation pairs · {flagged} to review "
            f"across {len(by_work)} works"
        )
        if flagged:
            self.stdout.write(
                "Check each against a KJV before editing: where the KJV and ASV "
                "rest on different manuscripts this reports a mismatch that "
                "isn't one."
            )
