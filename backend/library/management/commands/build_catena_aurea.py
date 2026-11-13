"""Build one volume of The Golden Chain: Thomas Aquinas's Catena Aurea on a
Gospel, whole, in Newman's Oxford translation, under the Open Word Bible.

Aquinas compiled the Catena Aurea for Pope Urban IV: under every verse of
the four Gospels, the Fathers' own words, linked one after another. It is
itself a catena, so unlike `build_catena` (which CHOOSES among many
commentators) this command publishes one work nearly whole, in its own
order. It reuses `build_catena`'s Gospel text, passages, layout, scan-damage
filter and writer; only the reading of Logia's text is its own.

    DJANGO_DEBUG=true uv run python manage.py build_catena_aurea /tmp/logia-en.json MAT

SOURCE TAGS. Logia's excerpts are pages of the Oxford edition, where each
Father's words open with his name as a siglum. Matthew and Mark come from
CCEL's typed edition, a paragraph per Father: "Chrys., Hom. in Matt., ii:
…". Luke and John come from archive.org's OCR of the printed volumes, the
sigla inline in capitals: "CHRYS. While all … AUG. The Greek word …". Each
siglum becomes a paragraph opening with the Father's name in full
(`CCEL_TAGS`, `ARCHIVE_TAGS`; "ID." is the same Father again). CCEL's
margin references ("Hom. in Matt., ii") are left out: the scanned volumes
lost theirs, and the four should read alike. Words before the first siglum
of an excerpt run on from the Father before; his name is set again there,
since a verse of the Gospel now stands between.

DAMAGE. Each Father's passage is read on its own and left out if the scan has
damaged it (`build_catena`'s `damaged`), if it carries Greek or Hebrew, if
its straight quotation marks do not pair, or if a stray capitalised word is
left in it (a siglum the OCR broke, or margin debris such as "SUP-"). A
CCEL paragraph that opens with a siglum the tables cannot read ("Theod. non
occ.:", which may be Theodotus or Theodoret) is left out too, never given to
the Father before it.
Every passage left out is listed in `data/catena/aurea/<CODE>/dropped.json`,
which each build rewrites.

LAYOUT. As `build_catena`: one chapter per chapter of the Gospel, OWB's
section headings as `<h3>`, each verse (or run of verses) quoted once, then
the chain on it, in Aquinas's order. The chain is long, so a Gospel chapter
that would pass PART_WORDS is cut into parts at OWB's section breaks, each
titled by its verses ("Matthew 5:1–12"); a single section longer than that
stays whole. Mark is built here though `build_catena` leaves it out: its
endings begin inside 16:8 (`text_block`). An introduction opens the volume
(`data/catena/aurea/introduction.html`, shared by the four) and a chapter
on the Fathers and the edition closes it.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from django.core.management.base import CommandError

from library import english_audit
from library.management.commands import build_catena
from library.management.commands.build_catena import (
    _ELISION,
    _NON_LATIN,
    BOOKS,
    EDITORIAL,
    LOGIA,
    curl_singles,
    span,
    tidy,
    vendor_owb,
    verse_key,
)
from library.management.commands.build_owb_book import DISPUTED
from library.text import word_count

#: Gospel code -> (Logia work, volume in the series).
VOLUMES = {
    "MAT": ("catena-matthew", 1),
    "MRK": ("catena-mark", 2),
    "LUK": ("catena-luke", 3),
    "JHN": ("catena", 4),
}
#: build_catena's books, and Mark, which that command leaves out until its
#: disputed endings are handled; this one handles them (`text_block`).
GOSPELS = {**BOOKS, "MRK": ("Mark", 41, "Mark {n}", "The Gospel text")}
#: OWB's note on Mark's endings, which begin at the second sentence of 16:8.
MARK_ENDINGS = next(note for first, _, note in DISPUTED if first == "MRK.16.8.s2")
#: A volume's chapter is cut into parts, at OWB's section breaks, near this many words.
PART_WORDS = 8000
AUTHOR = "aquinas"
SERIES = "the-golden-chain"
FOLDER = EDITORIAL / "aurea"

#: CCEL's sigla (Matthew, Mark), as each paragraph opens, before its margin
#: reference and colon -> the Father's name. Built from the data: every
#: distinct opening with its count is in the module's history; the misspelt
#: ones ("Theophlyact", "Psuedo-Chrys.") are CCEL's typing slips.
CCEL_TAGS = {
    "Chrys.": "Chrysostom", "Chrys": "Chrysostom", "Chyrs.": "Chrysostom", "Chrysostom": "Chrysostom",
    "Pseudo-Chrys.": "Pseudo-Chrysostom", "Pseudo-Chyrs.": "Pseudo-Chrysostom",
    "Psuedo-Chrys.": "Pseudo-Chrysostom",
    "Aug.": "Augustine", "Aug": "Augustine", "Augustine": "Augustine",
    "Pseudo-Aug.": "Pseudo-Augustine", "Psuedo-Aug.": "Pseudo-Augustine",
    "Pseudo-Augustine": "Pseudo-Augustine",
    "Jerome": "Jerome", "Pseudo-Jerome": "Pseudo-Jerome",
    "Bede": "Bede",
    "Remig.": "Remigius", "Remig": "Remigius", "Remigius": "Remigius",
    "Theophylact": "Theophylact", "Theophlyact": "Theophylact", "Theophyact": "Theophylact",
    "Hilary": "Hilary", "Hil.": "Hilary",
    "Origen": "Origen", "Origin": "Origen", "Pseudo-Origen": "Pseudo-Origen",
    "Greg.": "Gregory", "Greg": "Gregory", "Gregory": "Gregory",
    "Greg. Nyss.": "Gregory of Nyssa", "Gregory Nyss.": "Gregory of Nyssa",
    "Raban.": "Rabanus", "Raban": "Rabanus", "Rabanus": "Rabanus",
    "Gloss.": "Gloss", "Gloss": "Gloss", "Gloss. Ordinaria": "Gloss", "Gloss. Anselm": "Gloss",
    "Ambrose": "Ambrose", "Ambrose.": "Ambrose", "Ambrosiaster": "Ambrosiaster",
    "Leo": "Leo", "Cyprian": "Cyprian",
    "Chrysol.": "Chrysologus", "Chrysol": "Chrysologus", "Chrysologus": "Chrysologus",
    "Severianus": "Severianus", "Cassian": "Cassian",
    "Cyril": "Cyril", "Cyril of Alexandria": "Cyril of Alexandria",
    "Haymo": "Haymo", "Euseb.": "Eusebius",
    "Pseudo-Athan.": "Pseudo-Athanasius",
    "Isidore": "Isidore", "Isid.": "Isidore",
    "Theodotus": "Theodotus",
    "Damascenus": "Damascene", "Damas.": "Damascene", "Damasc.": "Damascene",
    "Titus": "Titus of Bostra",
    "Gennadius": "Gennadius", "The Council of Ephesus": "The Council of Ephesus",
    "Second Council of Constantinople": "The Second Council of Constantinople",
    "Petrus Alfonsus": "Petrus Alfonsus", "Pseudo-Dionysius": "Pseudo-Dionysius",
    "Dionys.": "Dionysius", "Dionysius": "Dionysius",
    "Josephus": "Josephus", "Maximus": "Maximus", "Faustus": "Faustus", "Nemesius": "Nemesius",
    "Anselm": "Anselm", "Paschasius": "Paschasius", "Lanfranc": "Lanfranc",
    "Aug. Serm.": "Augustine", "Aug. Quaest. Ev.": "Augustine",
}

#: The scanned volumes' sigla (Luke, John), as the OCR prints them -> the
#: Father's name. Spaces inside a siglum stand for any run of spaces, so the
#: OCR's broken "TH EOPHYL." is listed as it reads. A capitalised word not
#: here is not read as a siglum, and its passage is left out as damaged.
ARCHIVE_TAGS = {
    "CHRYS.": "Chrysostom", "CHRYSOSTOM": "Chrysostom", "CHRY.": "Chrysostom", "CHRIS.": "Chrysostom",
    "CHUYS.": "Chrysostom", "CORYS.": "Chrysostom",
    "PSEUDO-CHRYS.": "Pseudo-Chrysostom", "PSEDUO-CHRYS.": "Pseudo-Chrysostom",
    "PSEUDO-CHKYS.": "Pseudo-Chrysostom",
    "AUG.": "Augustine", "AUGUSTINE": "Augustine", "PSEUDO-AUG.": "Pseudo-Augustine",
    "BEDE": "Bede", "BEDS.": "Bede",
    "AMBROSE": "Ambrose", "AMBRQSE": "Ambrose", "BROSE": "Ambrose",
    "THEOPHYL.": "Theophylact", "THEOPHYLACT": "Theophylact", "THE OPHYL.": "Theophylact",
    "TH EOPHYL.": "Theophylact", "TH EO PH YL.": "Theophylact",
    "CYRIL": "Cyril", "CYRIL OF JER US.": "Cyril of Jerusalem",
    "GREG. NYSS.": "Gregory of Nyssa", "Greg. NYSS.": "Gregory of Nyssa",
    "GREG. NAZ.": "Gregory of Nazianzus",
    "GREG.": "Gregory", "G REG.": "Gregory",
    "ORIGEN": "Origen", "ORIG.": "Origen", "OIUGEN": "Origen",
    "ALCUIN": "Alcuin", "ALCUIX.": "Alcuin", "ALCUJN.": "Alcuin",
    "BASIL": "Basil",
    "GREEK EXPOSITOR": "Greek Expositor", "GREEK EX.": "Greek Expositor", "GREEK Ex.": "Greek Expositor",
    "GREEK": "Greek Expositor",
    "EUSEB.": "Eusebius", "EUSEBIUS": "Eusebius",
    "TITUS BOSTRENSIS": "Titus of Bostra", "TIT. BOST.": "Titus of Bostra", "TITUS BOST.": "Titus of Bostra",
    "TITUS Bos.": "Titus of Bostra", "TITUS Bos": "Titus of Bostra", "TIT.": "Titus of Bostra",
    "TITUS": "Titus of Bostra",
    "GLOSS.": "Gloss",
    "ATHAN.": "Athanasius", "ATHANASIUS": "Athanasius", "A THAN AS.": "Athanasius",
    "HILARY": "Hilary", "JEROME": "Jerome", "HAYMO.": "Haymo",
    "EPIPH.": "Epiphanius", "EP I PH AN.": "Epiphanius",
    "ISID. PE LE US": "Isidore of Pelusium", "ISIDORE": "Isidore", "ISID.": "Isidore",
    "MAXIM.": "Maximus", "MAXIMUS": "Maximus", "MAX.": "Maximus",
    "DAMAS.": "Damascene", "DAMASC.": "Damascene", "DAMASCENE": "Damascene",
    "CYPRIAN": "Cyprian",
    "ID.": None,  # idem: the same Father again, from another of his works
}
#: The same sigla set in capitals and small capitals, which part of the scanned
#: John (and a few pages of Luke) reads as ordinary case: "Aug. The Greek…".
#: Read only where a sentence or clause has just ended and another begins,
#: since the OCR also sets margin references in the line ("bad Aug. men").
ARCHIVE_MIXED_TAGS = {
    "Aug.": "Augustine", "Aug;": "Augustine", "Chrys.": "Chrysostom", "Theophyl.": "Theophylact",
    "Greg. Nyss.": "Gregory of Nyssa", "Greg.": "Gregory", "Alcuin.": "Alcuin",
    "Origen.": "Origen", "Origen;": "Origen", "Bede.": "Bede", "Bede;": "Bede",
    "Hilary.": "Hilary", "Didymus.": "Didymus", "Didym.": "Didymus", "Orig.": "Origen", "Gloss.": "Gloss", "Jerome.": "Jerome",
    "Ambrose.": "Ambrose", "Cyril;": "Cyril",
}

#: A siglum and what follows it: an optional stop, comma, semicolon or colon
#: (the OCR prints "AMBROSE;" and "CHRYS," alike) and the space before the text.
def _siglum(tag: str) -> str:
    """A siglum's spelling for lookup: single-spaced, without its final stop."""
    return " ".join(tag.split()).rstrip(".")


_ARCHIVE_NAMES = {_siglum(t): name for t, name in ARCHIVE_TAGS.items()}
_ARCHIVE_TAG = re.compile(
    r"(?<![\w-])(?P<tag>"
    + "|".join(
        r"\s*".join(map(re.escape, t.split())) for t in sorted(_ARCHIVE_NAMES, key=len, reverse=True)
    )
    + r")(?![\w])\s*[.;,:\-]*\s*"
    + r"|(?:^|(?<=[.,;?!:\"'’”)] ))(?P<mixed>"
    + "|".join(map(re.escape, sorted(ARCHIVE_MIXED_TAGS, key=len, reverse=True)))
    + r")\s+(?=[A-Z\"'])"
)
#: A CCEL paragraph's opening: the siglum, its margin reference, the colon.
_CCEL_OPENING = re.compile(
    r"^(?P<name>[A-Z][^,:]{0,40}?)(?:,(?P<cite>(?:[^:]|(?<=\d):(?=\d)){0,200}))?:(?:\s+|$)"
)
#: A second margin reference after the siglum's colon ("Chrys.: Hom., xxii:",
#: "Jerome: Hierom. ad Pammach, Epist 57:"): abbreviations, numerals and
#: short words only, up to its own colon, and a numeral or an abbreviation's
#: stop among them, so that "Otherwise:" or "The sense therefore is:" stays.
_SECOND_CITE = re.compile(
    r"^(?=[^:]*(?:\d|\b[ivxlc]+\b|\w\.))(?:(?:[A-Z]\w*\.?|[ivxlc]+\.?|\d+|[a-z]{1,3}\.?),?\s*){1,8}:\s+"
)
#: Letter runs that are not words but read true in this edition: the "s" of a
#: possessive, and the abbreviations of its references ("i. e.", "c.", "Ps.",
#: "St.", "ap.", "Ex.", "Ki.").
ABBREVIATIONS = frozenset({"s", "e", "c", "ps", "ap", "ex", "st", "ki", "ep", "viz"})
#: An old second- or third-person verb: its stem, then -est, -eth, -st, -edst.
_ARCHAIC = re.compile(r"^([a-z]+?)(?:edst|est|eth|st)$")
#: A lower-case word set alone between two sentences, "rise again. laid. I
#: marvel": a margin note the OCR read into the text.
_STRAY_WORD = re.compile(r"(?<=[a-z]{3}[.?!] )(?<!viz\. )[a-z]+\.(?= [A-Z]|$)")
#: A margin reference the OCR set in the line: a siglum in small capitals ("the
#: glory and Chrys. crown"), the editor's "ubi sup." / "ut sup." / "non occ.",
#: or a chapter numeral in capitals ("XVIII.").
_STRAY_SIGLUM = re.compile(
    r"\b(?:Chrys|Aug|Theophyl|Greg|Orig|Didym)\.|\b(?:ubi|ut) sup\b|\bnon occ\b|\b(?!LXX\b)[IVXLC]{2,}\b"
)
#: A CCEL opening that is a siglum (an abbreviated name) even when the table
#: cannot read it: its first word ends in a stop.
_SIGLUM_LIKE = re.compile(r"[A-Z][\w-]*\.(?:\s|$)")
#: The speaker of a passage whose siglum could not be read.
UNREAD = "\0unread"
#: A reference CCEL wrote as a range of one verse, "[Tit 3:11-11]" -> "3:11".
_ONE_VERSE_RANGE = re.compile(r"\b(\d+:(\d+))-\2\b")
#: A capitalised word the sigla did not account for: a broken siglum or margin debris.
_STRAY_CAPS = re.compile(r"\b(?!(?:LORD|GOD|LXX|AMEN)\b)(?![IVXLC]+\b)[A-Z]{2,}\b")


def ccel_name(opening: str) -> str | None:
    """The Father a CCEL paragraph's opening names, or None if it names none.
    The siglum may carry the rest of its reference before the colon ("Gloss.
    ord.", "Augustine ...", "Bede; see Ambr. in Luc. 6"); a phrase that only
    looks like an opening ("It goes on:") names no one."""
    # "Cyril ... :" — the scan's ellipsis for a lost reference, closed up by tidy
    opening = re.sub(r"\s*(?:\.\.\.|…)$", "", opening.split(";")[0].strip())
    if opening in CCEL_TAGS:
        return CCEL_TAGS[opening]
    words = opening.split()
    for k in range(len(words) - 1, 0, -1):
        head, rest = " ".join(words[:k]), " ".join(words[k:])
        if head in CCEL_TAGS and (head.endswith(".") or rest.startswith("...") or re.search(r"\d", rest)):
            return CCEL_TAGS[head]
    return None


def ccel_segments(text: str) -> list[tuple[str | None, list[str]]]:
    """[(Father or None for a run-on, [paragraphs])] from a CCEL excerpt. An
    opening that is a siglum this table cannot read ("Theod. non occ.:") names
    UNREAD, so its passage is left out rather than joined to the Father
    before it."""
    out: list[tuple[str | None, list[str]]] = []
    for para in tidy(text):
        m = _CCEL_OPENING.match(para)
        name = ccel_name(m["name"]) if m else None
        if not name and m and _SIGLUM_LIKE.match(m["name"]):
            name = UNREAD
        if name:
            out.append((name, [_SECOND_CITE.sub("", para[m.end() :], count=1)]))
        elif out:
            out[-1][1].append(para)
        else:
            out.append((None, [para]))
    return out


def archive_segments(text: str) -> list[tuple[str | None, list[str], bool]]:
    """[(Father or None for a run-on, [paragraphs], idem)] from a scanned excerpt."""
    out = []
    flat = " ".join(tidy(text))
    at, name, idem = 0, None, False
    for m in _ARCHIVE_TAG.finditer(flat):
        chunk = flat[at : m.start()].strip()
        if chunk or at:
            out.append((name, [chunk], idem))
        if m["mixed"]:
            name, idem = ARCHIVE_MIXED_TAGS[m["mixed"]], False
        else:
            tag = _siglum(m["tag"])
            name, idem = _ARCHIVE_NAMES[tag], tag == "ID"
        at = m.end()
    out.append((name, [flat[at:].strip()], idem))
    return [(n, ps, i) for n, ps, i in out if any(ps)]


class Command(build_catena.Command):
    help = "Build one volume of The Golden Chain (Aquinas's Catena Aurea) from Logia and the Open Word Bible."

    author_slug = "thomas-aquinas"
    books = GOSPELS

    def add_arguments(self, parser):
        parser.add_argument("logia", help="path to logia-en.json (https://logia.faith/downloads/logia-en.json)")
        parser.add_argument("code", choices=sorted(VOLUMES), help="the Gospel, e.g. MAT")
        parser.add_argument(
            "--vendor-owb", metavar="CHECKOUT",
            help="first write data/catena/<CODE>/owb_sections.json from an open-word-bible checkout",
        )

    # --- inputs -------------------------------------------------------------

    def load(self, path: str, code: str):
        logia = self.read_logia(path)
        self.code = code
        work_id, self.volume = VOLUMES[code]
        self.folder = FOLDER / code
        self.meta = json.loads((self.folder / "book.json").read_text("utf-8"))
        self.work = logia["works"][work_id]
        mine = [e for e in logia["excerpts"] if e["work"] == work_id and e["author"] == AUTHOR]
        self.load_owb(code)
        # OWB's one spaced ellipsis in the Gospels (Mark 11:32), set as one mark.
        self.verses = {v: t.replace(" . . .", " …") for v, t in self.verses.items()}
        _ = self.open_at  # read from the whole verses, before text_block cuts Mark 16:8 in two
        scanned = "archive.org" in mine[0]["source_url"]
        self.scanned = scanned
        # Logia lists a work's excerpts in the work's order; hold it to that.
        starts = [verse_key(e["start"]) for e in mine]
        if starts != sorted(starts):
            raise CommandError(f"{work_id}: Logia's excerpts are not in the order of the Gospel")
        self.read_chain(mine, scanned)

    def read_chain(self, excerpts: list[dict], scanned: bool) -> None:
        """Split every excerpt into its Fathers' passages, keep the sound
        ones, and note the rest in self.dropped."""
        self.excerpts, self.dropped, self.order = {}, [], {}
        speaker = None
        for n, e in enumerate(excerpts):
            kept = []
            if scanned:
                segments = archive_segments(e["text"])
            else:
                segments = [(name, paras, False) for name, paras in ccel_segments(e["text"])]
            for k, (name, paras, idem) in enumerate(segments):
                if idem:
                    name = speaker
                speaker = name or speaker
                if not "".join(paras).strip():
                    continue  # a siglum alone at an excerpt's end: its words open the next
                why = (
                    "an opening siglum this build cannot read (dropped, not given to the Father before)"
                    if speaker == UNREAD
                    else self.unsound(paras)
                )
                if why:
                    self.dropped.append({"excerpt": e["id"], "passage": k + 1, "father": speaker,
                                         "why": why, "text": " ".join(paras)})
                else:
                    kept.append((speaker, paras))
            if kept:
                e["_start"], e["_end"] = verse_key(e["start"]), verse_key(e["end"])
                e["_segments"] = kept
                self.excerpts[e["id"]] = e
                self.order[e["id"]] = n
        self.total = len(excerpts)

    def known(self, word: str) -> bool:
        """A word the library prints (`vocabulary`), a reference's abbreviation,
        or an old verb form whose stem it prints: "graspest", "seduceth",
        "returnedst" — the Oxford translators' English, not the scan's."""
        w = word.lower()
        if w in self.vocabulary or w in ABBREVIATIONS:
            return True
        m = _ARCHAIC.match(w)
        return bool(m) and len(m[1]) > 2 and any(stem in self.vocabulary for stem in (m[1], m[1] + "e"))

    def damaged(self, text: str) -> bool:
        """`debris` for a typed volume; for a scanned one, also any word the
        library does not know, since that is how the OCR's misreadings show."""
        if self.debris(text):
            return True
        # A rare old form the audit reads as two words run together ("shewest",
        # she + west) cannot be told from a real fusion here either.
        if any(english_audit._word_fusion(text, english_audit.library_word_counts())):
            return True
        return self.scanned and not all(map(self.known, english_audit._WORD.findall(text)))

    def unsound(self, paras: list[str]) -> str | None:
        """Why one Father's passage cannot stand, or None if it can. A straight
        mark (the scans') must pair; a curled one (CCEL's) must not close a
        quotation that never opened."""
        text = " ".join(paras)
        if _NON_LATIN.search(text):
            return "Greek or Hebrew"
        if self.damaged(text):
            return "a misread or broken word" if not self.scanned else "the scan has damaged it"
        if _STRAY_CAPS.search(text):
            return "a stray capitalised word (a broken siglum or margin debris)"
        if self.scanned and (_STRAY_WORD.search(text) or _STRAY_SIGLUM.search(text)):
            return "margin debris read into the line"
        if text.count('"') % 2 or any(english_audit._orphan_quotes(paras)):
            return "an unpaired quotation mark"
        return None

    # --- rendering ----------------------------------------------------------

    def passages(self) -> list[tuple[str, list[tuple[int, int]]]]:
        """build_catena's passages, except that OWB's section for Mark's short
        ending begins inside 16:8, at its second sentence: 16:8 stays with the
        passage before, and the section's heading moves into the verse
        (`text_block`)."""
        out = super().passages()
        self.short_ending = None
        if self.code == "MRK":
            at = next(i for i, (_, vs) in enumerate(out) if vs[0] == (16, 8))
            self.short_ending, verses = out.pop(at)
            out[at - 1][1].extend(verses)
        return out

    def text_block(self, code: str, verses: list[tuple[int, int]]) -> str:
        """build_catena's quoted block, except at Mark 16:8. Its first sentences
        are the Gospel as the earliest manuscripts end it, quoted here, and the
        Fathers on them follow; its bracketed rest is the short ending, which
        `passage_html` sets after them, under OWB's own note on the endings and
        the short ending's heading. So 16:8 itself is not called disputed, and
        16:9-20 follow in their brackets as OWB prints them."""
        end = (16, 8)
        if code != "MRK" or end not in verses:
            return super().text_block(code, verses)
        if verses[-1] != end:
            raise CommandError("Mark 16:8 must close its passage (see passages)")
        whole = self.verses[end]
        cut = whole.index(" [")
        try:
            self.verses[end] = whole[:cut]
            block = super().text_block(code, verses)
            self.verses[end] = whole[cut + 1 :]
            self.endings = (
                f"<p><em>{escape(MARK_ENDINGS)}</em></p><h3>{escape(self.short_ending)}</h3>"
                + super().text_block(code, [end])
            )
        finally:
            self.verses[end] = whole
        return block

    def passage_html(self, code: str, title: str, verses, ids: list[str]) -> str:
        """build_catena's passage, then Mark's short ending if 16:8 closed it."""
        self.endings = ""
        html = super().passage_html(code, title, verses, ids)
        return html + "\n" + self.endings if self.endings else html

    def order_key(self, e: dict):
        return self.order[e["id"]]

    def excerpt_html(self, e: dict) -> str:
        parts = []
        for name, paras in e["_segments"]:
            for i, para in enumerate(paras):
                para = _ONE_VERSE_RANGE.sub(r"\1", para)
                text = escape(curl_singles(_ELISION.sub("’", para)), quote=False)
                if i == 0 and name:
                    text = f"<strong>{escape(name)}</strong>: {text}"
                parts.append(f"<p>{text}</p>")
        return "\n".join(parts)

    def fathers(self, ids) -> Counter:
        return Counter(name for i in ids for name, _ in self.excerpts[i]["_segments"] if name)

    voices_label = "The chain:"

    # --- main ---------------------------------------------------------------

    def handle(self, *args, **opts):
        code = opts["code"]
        if opts["vendor_owb"]:
            vendor_owb(Path(opts["vendor_owb"]), code)
        self.load(opts["logia"], code)
        passages = self.passages()
        firsts = [vs[0] for _, vs in passages]
        homes = defaultdict(list)
        for i, e in self.excerpts.items():
            # One keyed before the first verse (a heading, "MRK.1.0") opens the book.
            e["_start"], e["_end"] = max(e["_start"], firsts[0]), max(e["_end"], firsts[0])
            at = max(n for n, v in enumerate(firsts) if v <= e["_start"])
            homes[at].append(i)

        chapters = defaultdict(list)
        for n, (title, verses) in enumerate(passages):
            home = Counter(c for c, _ in verses).most_common(1)[0][0]
            chapters[home].append((title, verses, sorted(homes[n], key=self.order.get)))

        name = self.books[code][0]
        intro = (FOLDER / "introduction.html").read_text("utf-8").replace("{gospel}", name)
        bodies = [("Introduction", intro, "")]
        used = Counter()
        self.whole_sections = []
        for number in sorted(chapters):
            used.update(self.fathers(i for _, _, ids in chapters[number] for i in ids))
            parts = self.parts(code, chapters[number])
            for k, (verses, html, ids) in enumerate(parts):
                names = [f for f, _ in self.fathers(ids).most_common()]
                if len(parts) == 1:
                    title = self.books[code][2].format(n=number)
                else:
                    title = span(code, verses[0], verses[-1], self.books)
                # The chapter's summary heads its first part; each part names its own voices.
                summary = self.summary(number, names) if k == 0 else self.voices_sentence(names)
                bodies.append((title, html, summary))
        bodies.append(("The Fathers and the Edition", self.edition_html(used), ""))
        book = self.write(bodies)
        flagged = [
            f"{ch.title} ({ch.word_count:,})"
            for ch in book.chapters.order_by("order")
            if ch.word_count > PART_WORDS
        ]
        self.write_dropped()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        kept = sum(len(e["_segments"]) for e in self.excerpts.values())
        self.stdout.write(
            f"{len(self.excerpts)} of {self.total} excerpts used; {kept} passages kept, "
            f"{len(self.dropped)} left out (dropped.json)"
        )
        if flagged:
            self.stdout.write(f"chapters over {PART_WORDS:,} words: " + ", ".join(flagged))
        for title in self.whole_sections:
            self.stdout.write(f"one OWB section alone passes {PART_WORDS:,} words: {title}")

    def parts(self, code: str, passages: list) -> list[tuple[list, str, list]]:
        """A Gospel chapter as one or more parts, [(its verses, html, excerpt ids)], cut at
        OWB's section breaks: sections are added to a part until the next would
        take it past PART_WORDS. A section longer than that is a part of its
        own, whole (noted in self.whole_sections)."""
        out: list[tuple[list, list[str], list, int]] = []
        for title, verses, ids in passages:
            html = self.passage_html(code, title, verses, ids)
            words = word_count(html)
            if words > PART_WORDS:
                self.whole_sections.append(f"{span(code, verses[0], verses[-1], self.books)} ({words:,})")
            if out and out[-1][3] + words <= PART_WORDS:
                vs, htmls, part_ids, total = out[-1]
                out[-1] = (vs + verses, [*htmls, html], part_ids + ids, total + words)
            else:
                out.append((list(verses), [html], list(ids), words))
        return [(vs, "\n".join(htmls), part_ids) for vs, htmls, part_ids, _ in out]

    def write_dropped(self) -> None:
        (self.folder / "dropped.json").write_text(
            json.dumps(
                {
                    "_note": [
                        "Passages of the Catena Aurea that build_catena_aurea leaves out, with the reason:",
                        "each is one Father's words within a Logia excerpt (passage = its place there).",
                        "Rewritten by every build; the scan's text is kept so an editor can repair one.",
                    ],
                    "logia_sha256": self.logia_sha,
                    "dropped": self.dropped,
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            "utf-8",
        )

    def edition_html(self, used: Counter) -> str:
        """The back chapter: the editorial account, then the Fathers heard in
        this volume, then the edition."""
        intro = (FOLDER / "edition.html").read_text("utf-8")
        rows = ["<h2>The Fathers in this volume</h2>"]
        listed = sorted(used.items(), key=lambda kv: (-kv[1], kv[0]))
        rows.append(
            "<p>Here is every voice Aquinas calls on in this volume, with the number of times he speaks, "
            "most often first.</p>"
        )
        rows.append(
            "<ul>"
            + "".join(f"<li>{escape(n)}: {c}</li>" for n, c in listed)
            + "</ul>"
        )
        rows.append("<h2>The edition</h2>")
        source = "CCEL (ccel.org)" if not self.scanned else "the University of Toronto’s scan on archive.org"
        rows.append(
            f"<p><em>{escape(self.work['title'])}</em>. {escape(self.edition())}. "
            f"The text here is from {source}, as gathered by Logia (logia.faith), which offers it under CC0. "
            f"{self.dropped_note()}</p>"
        )
        rows.append(
            f"<p>{self.bible_note()}</p>"
        )
        return intro + "\n" + "\n".join(rows)

    def dropped_note(self) -> str:
        if not self.dropped:
            return ""
        n = len(self.dropped)
        damage = "the scan has damaged them past sure reading" if self.scanned else "a word or a quotation mark is broken"
        return (
            f"Where a Father’s words turn on Greek or Hebrew letters, or {damage}, his passage is left "
            f"out rather than guessed at: {n} passage{'s' if n != 1 else ''} in this volume."
        )

    def edition(self) -> str:
        """Logia's account of the translation, its year ranges with an en dash."""
        return re.sub(r"(\d)-(\d)", "\\1–\\2", self.work["translation"].split(";")[0])

    def attribution(self) -> str:
        return (
            f"Thomas Aquinas, {self.work['title']}; {self.edition()}; "
            f"text from Logia ({LOGIA}, CC0). {self.scripture_credit()}"
        )

    def extra_fields(self) -> dict:
        from library.models import Series

        return {"series": Series.objects.get(slug=SERIES), "series_position": self.volume}

