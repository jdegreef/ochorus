"""Build F. F. Bosworth's *Christ the Healer: Sermons on Divine Healing* (1924).

The FIRST EDITION only. The book was enlarged from 1948 on, with Robert
Bosworth's additions, and those later editions — and every modern reprint and
online text descended from them — are in copyright. The source is the Internet
Archive scan of Princeton Theological Seminary's copy
(`christhealerserm00bosw_0`), whose title page reads "Copyright, 1924, by F. F.
Bosworth".

That copy is a slightly LATER printing of the 1924 book than the first. It is
set from the same plates for pages 1–172, but it adds a note at the end of
Sermon IV pointing the reader to a supplement, eight more pages of testimonies
(pp. 173–180, one from a reader who "got the Evangelist's book 'Christ the
Healer'" at a later campaign) and the supplement itself, "Appropriating Faith"
(pp. 181–189). The Master's College copy (`christhealerserm0000evag`) has none
of the three: its Sermon IV runs straight into Sermon V and its testimonies end
on p. 172. So this command takes pp. 1–172 and drops the note — the first
printing's text, and exactly what its Contents lists:

    Sermon I    Did Jesus Redeem Us From Our Diseases When He Atoned for Our Sins?
    Sermon II   Is Healing for All?
    Sermon III  The Lord's Compassion
    Sermon IV   How to Appropriate the Redemptive and Covenant Blessing of Bodily Healing
    Sermon V    Paul's "Thorn"
                Thirty-one Questions
                Testimonies

`import_archive` can't chapter it: it splits on "CHAPTER" markers and this book
has none — each sermon opens under its title in capitals. So the seven openings
are named below and found in document order, and the reflow is
`import_archive`'s, plus two things this book needs:

* **Subheads.** The sermons are cut into sections under ALL-CAPS heads, and
  each testimony has a title-case headline; both become `<h3>`.
* **The Princeton copy's marginalia.** A reader pencilled notes in its margins,
  which the OCR reads as capital-letter lines ("WAS BASED EN THE SAME") that
  look exactly like subheads. A head therefore has to appear in the second scan
  of this printing too — Phillips Academy's copy (`christhealerserm0000fred`),
  which is clean — or it is dropped as a pencil note.

Dropped as furniture: the title page, the library stamp, the Preface (it is the
book's description), the Contents, running heads and page numbers. OCR slips in
the prose are repaired in `corrections.py`, settled against the Phillips scan.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/christ-the-healer.en.json`, resolving the existing
`f-f-bosworth` author. No `catalog.py` entry, so no importer can re-chapter it.
Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_christ_the_healer
"""

from __future__ import annotations

import html
import re
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, clean_title, word_count
from library.management.commands.import_archive import (
    _BAR_RULE,
    _BARE_NUM,
    _HYPHEN_EOL,
    _HYPHEN_SPACE,
    _NON_LETTER,
    _WS,
    _is_header,
    fetch_text,
)
from library.models import Author, Book, Chapter
from library.titlecase import MINOR

SLUG = "christ-the-healer"
TITLE = "Christ the Healer"
SUBTITLE = "Sermons on Divine Healing"
AUTHOR_SLUG = "f-f-bosworth"
ARCHIVE_ID = "christhealerserm00bosw_0"
#: The second scan of the same printing: the witness a subhead must appear in.
WITNESS_ID = "christhealerserm0000fred"
PUBLICATION_YEAR = 1924
COVER_COLOR = "#7a3b2e"  # warm oxblood — house-style cover ground

DESCRIPTION = (
    "Five sermons on divine healing, published in 1924 at the urging of the "
    "ministers and others in the cities where Bosworth had held revival "
    "campaigns across the United States and Canada. Written, as his preface "
    "admits, under great pressure and weariness between revivals, they make "
    "no pretence to literary style; their one aim is the simplest possible "
    "statement of the argument — that bodily healing, like forgiveness, was "
    "provided for in Christ's atonement, that it is God's will to heal, and "
    "how the sick may appropriate it by faith in His word. Bosworth answers "
    "the common objections, Paul's \"thorn\" among them, and closes with "
    "thirty-one questions and testimonies of those healed in his meetings."
)

ATTRIBUTION = (
    "Public domain — F. F. Bosworth, Christ the Healer: Sermons on Divine "
    "Healing (Racine, Wis.: the author, 1924), the first edition. Text from "
    "the Internet Archive scan of Princeton Theological Seminary's copy "
    "(christhealerserm00bosw_0), pages 1–172, checked against Phillips "
    "Academy's (christhealerserm0000fred). Not the enlarged edition of 1948 "
    "and after, which is in copyright."
)

#: (stored title, the opening heading line(s) as the scan prints them). Order
#: IS the reading order, and each heading is looked for after the previous one.
CHAPTERS: list[tuple[str, tuple[str, ...]]] = [
    ("Did Jesus Redeem Us from Our Diseases When He Atoned for Our Sins?",
     ("DID JESUS REDEEM US FROM OUR DISEASES", "WHEN HE ATONED FOR OUR SINS?")),
    ("Is Healing for All?", ("IS HEALING FOR ALL?",)),
    ("The Lord’s Compassion", ("THE LORD’S COMPASSION",)),
    ("How to Appropriate the Redemptive and Covenant Blessing of Bodily Healing",
     ("HOW TO APPROPRIATE", "The Redemptive and Covenant Blessing of Bodily Healing")),
    ("Paul’s Thorn", ("PAUL’S “THORN”",)),
    ("Thirty-One Questions", ("THIRTY-ONE QUESTIONS",)),
    ("Testimonies", ("TESTIMONIES",)),
]

#: The first printing ends here: the last line of p. 172.
LAST_LINE = "Miss R. Nix, 412 Dundas street, E., Toronto."

#: The later printing's note at the foot of Sermon IV, pointing to the
#: supplement it added (pp. 181–189). First line and last line, inclusive.
LATER_NOTE = ("NOTE: Let the reader next read", "(Pages 181 to 189).")

#: The running heads (verso is the book's title, recto the sermon's). With its
#: page number lost to a smudge, a running head reads as a section head, so
#: these are refused as heads wherever they turn up.
RUNNING_HEADS = (
    "CHRIST THE HEALER", "HEALING IN THE ATONEMENT", "IS HEALING FOR ALL?",
    "CHRIST’S COMPASSION FOR THE SICK", "HOW TO APPROPRIATE", "PAUL’S “THORN”",
    "THIRTY-ONE QUESTIONS", "TESTIMONIES",
)

#: Sermon I's two-column table of "Gospel parallels" (pp. 24–27). The OCR
#: reads its columns in no reliable order — row by row on p. 24, column by
#: column after — so it is transcribed here from the page images, a row per
#: pair, and replaces the scan's text between these two lines. Wording and
#: punctuation as printed, including the right column's unopened quotation in
#: the fifth row and the one sentence that runs across both columns.
PARALLELS_SPAN = ("“THE INNER MAN” “THE OUTER MAN”", "I will now cite one out of many hundreds of")
PARALLELS: list[tuple[str, str]] = [
    ("“The Inner Man”", "“The Outer Man”"),
    ("Adam, by his fall, brought sin into our souls.",
     "Adam, by his fall, brought disease into our bodies."),
    ("Sin is therefore the work of the devil.",
     "Disease is therefore the work of the devil. Jesus “went about doing good, and "
     "healing all that were oppressed of the devil.”"),
    ("Jesus was “manifested to destroy the works of the devil” in the soul.",
     "Jesus was “manifested to destroy the works of the devil” in the body."),
    ("The redemptive name “JEHOVAH-TSIDKENU” reveals His redemptive provision for our souls.",
     "The redemptive name “JEHOVAH-RAPHA” reveals His redemptive provision for our bodies."),
    ("On Calvary Jesus “bare our sins.”",
     "On Calvary Jesus bare our sicknesses.”"),
    ("He was made “sin for us” (II Cor. 5:21) when “He bare our sins.” (I Peter 2:24).",
     "He was “made a curse for us.” (Gal. 3:13) when He “bare our sicknesses.” (Matthew 8:17)."),
    ("“Who His own self bare our sins in His body on the tree.”",
     "“By whose stripes ye were healed.”"),
    ("“Who forgiveth all thine iniquities.”",
     "“Who healeth all thy diseases.”"),
    ("“For ye are bought with a price: therefore glorify God in your . . . spirit.”",
     "“For ye are bought with a price: therefore glorify God in your body . . . (I Cor. 6:20)."),
    ("The spirit is bought with a price.",
     "The body is bought with a price."),
    ("Is remaining in sin the way to glorify God in your spirit?",
     "Is remaining sick the way to glorify God in your body?"),
    ("Since He “bare our sins,” how many must it be God’s will to save, when they come to "
     "Him? “Whosoever believeth.”",
     "Since He “bare our sicknesses,” how many must it be God’s will to heal, when they come "
     "to Him? “He healed them all.”"),
    ("“As God ‘made Him to be sin for us who knew no sin’ ”—Rev. A. J. Gordon.",
     "“So God made Him to be sick for us who knew no sickness.”—Rev. A. J. Gordon."),
    ("“Since our Substitute bore our sins, did He not do so that we might not bare them?”—Rev. "
     "A. J. Gordon.",
     "“Since our Substitute bore our sicknesses, did He not do so that we might not bare "
     "them?”—Rev. A. J. Gordon."),
    ("“Christ bore our sins that we might be delivered from them. Not SYMPATHY—a suffering "
     "with, but SUBSTITUTION—a suffering for.”—Rev. A. J. Gordon.",
     "Christ bore our sicknesses that we might be delivered from them. Not SYMPATHY—a "
     "suffering with, but SUBSTITUTION—a suffering for."),
    ("“If the fact that Jesus ‘bore our sins in His own body on the tree’ be a valid reason "
     "why we should all trust Him now for the forgiveness of our sins,",
     "why is not the fact that He ‘bore our sicknesses’ an equally valid reason why we should "
     "all trust Him now to heal our bodies?” (Writer unknown)."),
    ("Faith for salvation “cometh by hearing” the Gospel—He “bare our sins.”",
     "Faith for healing “cometh by hearing”—He “bare our sicknesses.”"),
    ("Therefore, Preach the Gospel (that He bore our sins) to every creature,”",
     "and “the Gospel (that He bore our sicknesses) to every creature.”"),
    ("Christ’s promise for the soul (“shall be saved”) is in the great commission (Mark 16).",
     "Christ’s promise for the body (“shall recover”) is in the great commission. (Mark 16)."),
    ("In connection with the ordinance of baptism, the Bible teaches that he that believeth "
     "and is baptized shall be saved (Mark 16).",
     "In connection with the ordinance of anointing with oil, the Bible teaches that he that "
     "believeth and is anointed shall be healed. (James 5:14)."),
    ("We are commanded to baptize in Christ’s name.",
     "We are commanded to anoint “in the name of the Lord.” (James 5:14)."),
    ("In the Lord’s Supper the wine is taken “in remembrance” of His death for our souls. "
     "(I Cor. 11:25).",
     "In the Lord’s Supper the bread is eaten “in remembrance” of His death for our bodies. "
     "(I Cor. 11:23-24)."),
    ("The sinner is to repent before believing the Gospel “unto righteousness.”",
     "James 5:16 says, “Confess, therefore, your sins . . . that ye may be healed.”"),
    ("Water baptism stands for total surrender and obedience.",
     "Anointing with oil is the symbol and sign of consecration."),
    ("The sinner must accept God’s promise as true before he can feel the joy of salvation.",
     "The sick must accept God’s promise as true before he can feel well."),
    ("“As many as received Him . . . were born . . . of God.” (St. John 1:12-13).",
     "“As many as touched Him were made whole.” (Mark 6:56)."),
]

#: Sermon I's two renderings of Isaiah 53 (pp. 15–16): Young's and Leeser's,
#: set as verse with the verse numbers in a hanging column. The OCR tears the
#: numbers off and shuffles the two introductions into the verse, so these
#: are transcribed from the page images too, replacing the scan's text
#: between the two lines named. The unclosed quotation marks that open each
#: of Leeser's verses are as printed.
TRANSLATIONS_SPAN = (
    "I will here quote the learned translator, Dr.",
    "Rotherham’s translation of the 10th verse is",
)
YOUNG: list[tuple[str, list[str]]] = [
    ("3.", ["He is despised, and left of men,",
            "A man of pains (Heb., Makob), and acquainted with sickness (choli),",
            "And as one hiding the face from us,",
            "He is despised and we esteemed him not."]),
    ("4.", ["Surely our sicknesses (choli) he hath borne,",
            "And our pains (makob) he hath carried them,",
            "And we—we have esteemed him plagued,",
            "Smitten of God and afflicted."]),
    ("5.", ["And he is pierced for our transgressions,",
            "Bruised for our iniquities,",
            "The chastisement of our peace is on him,",
            "And by his bruise there is healing to us."]),
    ("6.", ["All of us like sheep have wandered,",
            "Each to his own way we have turned,",
            "And Jehovah hath caused to meet on him",
            "The punishment of us all."]),
    ("10.", ["And Jehovah hath delighted to bruise him;",
             "He hath made him sick (choli) ;",
             "If his soul doth make an offering for guilt,",
             "He seeth seed—he prolongeth days."]),
    ("12.", [". . . With transgressors he was numbered,",
             "And he the sin of many hath borne,",
             "And for transgressors he intercedeth."]),
]
LEESER: list[tuple[str, list[str]]] = [
    ("3.", ["“He was despised and shunned of men:",
            "A man of pains and acquainted with disease."]),
    ("4.", ["“But only our diseases did he bear himself,",
            "And our pains he carried."]),
    ("5.", ["“And through his bruises was healing granted to us."]),
    ("10.", ["“But the Lord was pleased to crush him through disease.”"]),
]


def _verse_html(verses: list[tuple[str, list[str]]]) -> str:
    return "<blockquote>" + "".join(
        f"<p>{num} " + "<br/>".join(html.escape(ln, quote=False) for ln in lines) + "</p>"
        for num, lines in verses
    ) + "</blockquote>"


def _translations_html() -> str:
    return (
        "<p>I will here quote the learned translator, Dr. Young, in his version of the Bible:</p>"
        + _verse_html(YOUNG)
        + "<p>Dr. Isaac Leeser, the able translator of the Hebrew English Bible, renders "
        "these verses as follows:</p>"
        + _verse_html(LEESER)
    )


def _parallels_html() -> str:
    """The table as a blockquote: the column heads, then a paragraph per row,
    the inner-man line above the outer-man line."""
    (inner, outer), *rows = PARALLELS
    out = [f"<p><b>{inner}</b><br/><b>{outer}</b></p>"]
    out += [f"<p>{html.escape(a, quote=False)}<br/>{html.escape(b, quote=False)}</p>"
            for a, b in rows]
    return "<blockquote>" + "".join(out) + "</blockquote>"


#: Sentinel line → the transcribed passage that replaces a span of the scan.
_SPLICES = [
    (PARALLELS_SPAN, "\x00parallels", _parallels_html),
    (TRANSLATIONS_SPAN, "\x00translations", _translations_html),
]
_SPLICED = {sentinel: render for _, sentinel, render in _SPLICES}


#: Chapters whose opening paragraph is a Scripture text set as an epigraph.
EPIGRAPH_CHAPTERS = {3, 5}

_TERMINAL = (".", "!", "?", "”", '"', ":", ";", ")")


def _norm(text: str) -> str:
    return _WS.sub(" ", re.sub(r"[^A-Za-z0-9 ]", " ", text)).strip().lower()


def _caps_share(line: str) -> float:
    letters = _NON_LETTER.sub("", line)
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0.0


def _is_caps_head(line: str) -> bool:
    """An ALL-CAPS section head: several letters, (nearly) all capitals, no digit."""
    letters = _NON_LETTER.sub("", line)
    return len(letters) >= 4 and _caps_share(line) >= 0.8 and not re.search(r"\d", line)


def _head_title(text: str) -> str:
    """An ALL-CAPS head in the corpus's title case ("GOD’S USE OF BODILY
    AFFLICTION" → "God’s Use of Bodily Affliction"), with the scan's stray
    marks at either end trimmed ("· THE EARNEST …", "… MERCIES ~")."""
    text = re.sub(r"^[^A-Za-z“‘]+|[^A-Za-z?’”]+$", "", text)
    text = re.sub(r"\s+([?!])", r"\1", text)

    def cap(word: str) -> str:
        return "-".join(
            re.sub(r"[A-Za-z]", lambda m: m.group(0).upper(), part.lower(), count=1)
            for part in word.split("-")
        )

    words = text.split()
    words = [
        w.lower() if 0 < i < len(words) - 1 and w.lower() in MINOR else cap(w)
        for i, w in enumerate(words)
    ]
    return clean_title(" ".join(words))


def _is_running_head(text: str) -> bool:
    key = _norm(text)
    return any(
        SequenceMatcher(None, _norm(h), key).ratio() >= 0.9 for h in RUNNING_HEADS
    )


def _is_junk(line: str) -> bool:
    """A line with no word in it — a smudge, rule or stamp fragment."""
    return not re.search(r"[A-Za-z]{2}", line)


#: The tail of a Scripture reference that wrapped onto a line of its own —
#: "(Psa. 25:" / "10)." — which is all digits and so reads as furniture.
_CITATION_TAIL = re.compile(r"^\d[\d\s:,-]*\)\.?\)?$")


def _attach_citation_tails(lines: list[str]) -> list[str]:
    """Put a wrapped reference's tail back on the line it wrapped from."""
    out: list[str] = []
    for line in lines:
        if _CITATION_TAIL.match(line.strip()):
            for k in range(len(out) - 1, -1, -1):
                if out[k].strip():
                    out[k] = out[k].rstrip() + ("" if out[k].rstrip().endswith((":", "-")) else " ") + line.strip()
                    break
            continue
        out.append(line)
    return out


def _find(lines: list[str], text: str, after: int, *, prefix: bool = False) -> int:
    for i in range(after, len(lines)):
        line = lines[i].strip()
        if line == text or (prefix and line.startswith(text)):
            return i
    raise CommandError(f"{text!r} not found after line {after} — the scan changed.")


def _blocks(lines: list[str]) -> list[list[str]]:
    """Runs of text lines, split at blank lines and page furniture."""
    out: list[list[str]] = []
    cur: list[str] = []
    for raw in lines:
        line = _BAR_RULE.sub(" ", raw).strip()
        line = _WS.sub(" ", line)
        if not line or _BARE_NUM.match(line) or _is_header(line) or _is_junk(line):
            if cur:
                out.append(cur)
                cur = []
            continue
        cur.append(line)
    if cur:
        out.append(cur)
    return out


def _join(lines: list[str]) -> str:
    text = ""
    for line in lines:
        if text and _HYPHEN_EOL.search(text):
            text = _HYPHEN_EOL.sub(r"\1", text) + line
        elif text.endswith("—") or line.startswith("—"):
            text += line  # the book closes up its dashes, across a line end too
        else:
            text = f"{text} {line}" if text else line
    return _HYPHEN_SPACE.sub(r"\1-\2", _WS.sub(" ", text).strip())


def _is_testimony_head(block: list[str]) -> bool:
    """A testimony's headline: one to three lines of title case, unpunctuated."""
    if len(block) > 3:
        return False
    text = _join(block)
    if text.endswith(_TERMINAL) or text.endswith(",") or re.search(r",\s*\d", text):
        return False
    words = [w for w in re.findall(r"[A-Za-z][\w’']*", text) if len(w) > 3]
    return bool(words) and sum(w[0].isupper() for w in words) / len(words) >= 0.75


def _chapter_body(lines: list[str], order: int, witness_heads: set[str],
                  dropped: list[str]) -> str:
    parts: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            parts.append(f"<p>{html.escape(_join(buf), quote=False)}</p>")
            buf.clear()

    for block in _blocks(_attach_citation_tails(lines)):
        if len(block) == 1 and block[0] in _SPLICED:
            flush()
            parts.append(_SPLICED[block[0]]())
            continue
        # A run of caps lines is a section head (it may wrap: "CHRIST'S
        # MERCIFUL ATTITUDE TOWARD OUR SICK- / NESSES …") — or a pencil note,
        # which can land anywhere, even inside a paragraph. Only the witness
        # can tell them apart.
        prose: list[str] = []
        i = 0
        while i < len(block):
            if not _is_caps_head(block[i]):
                prose.append(block[i])
                i += 1
                continue
            j = i
            while j < len(block) and _is_caps_head(block[j]):
                j += 1
            text = _join(block[i:j])
            if not _is_running_head(text) and _in_witness(text, witness_heads):
                buf.extend(prose)
                prose = []
                flush()
                parts.append(f"<h3>{html.escape(_head_title(text), quote=False)}</h3>")
            elif not _is_running_head(text):
                dropped.append(text)
            i = j
        if not prose:
            continue
        if order == 7 and not buf and _is_testimony_head(prose):
            parts.append(f"<h3>{html.escape(clean_title(_join(prose)), quote=False)}</h3>")
            continue
        buf.extend(prose)
        # A block that ends mid-sentence is a page break inside a paragraph:
        # keep accumulating.
        if _join(buf).endswith(_TERMINAL):
            flush()
    flush()
    body = "".join(parts)
    if order in EPIGRAPH_CHAPTERS:
        body = re.sub(r"^<p>(.*?)</p>", r"<blockquote><p>\1</p></blockquote>", body, count=1)
    return body


def _in_witness(text: str, heads: set[str]) -> bool:
    """Whether the witness prints this head too, allowing for OCR slips on
    either side ("COMPARISOW")."""
    key = _norm(text)
    return key in heads or any(
        abs(len(h) - len(key)) <= 4 and SequenceMatcher(None, h, key).ratio() >= 0.85
        for h in heads
    )


def _witness_heads(text: str) -> set[str]:
    """Every ALL-CAPS line of the witness scan, joined where it wraps."""
    heads: set[str] = set()
    run: list[str] = []
    for raw in text.split("\n") + [""]:
        line = raw.strip()
        if line and _is_caps_head(line):
            run.append(line)
            continue
        for i in range(len(run)):
            for j in range(i + 1, len(run) + 1):
                heads.add(_norm(_join(run[i:j])))
        run = []
    return heads


def _openings(lines: list[str]) -> list[int]:
    """The line each chapter's heading starts on, in reading order."""
    starts: list[int] = []
    after = _find(lines, "CONTENTS", 0)
    for _, heading in CHAPTERS:
        i = _find(lines, heading[0], after + 1)
        for k, more in enumerate(heading[1:], start=1):
            if lines[i + k].strip() != more:
                raise CommandError(f"heading {heading!r} continues {lines[i + k]!r}")
        starts.append(i)
        after = i
    return starts


def _cut(lines: list[str], first: int, last: int, keep: list[str]) -> list[str]:
    """``lines`` with ``lines[first:last]`` replaced by ``keep``."""
    return lines[:first] + keep + lines[last:]


def build_chapters(text: str, witness: str) -> tuple[list[tuple[str, str]], list[str]]:
    lines = text.split("\n")
    heads = _witness_heads(witness)
    starts = _openings(lines)

    # The later printing's note at the foot of Sermon IV.
    note_from = _find(lines, LATER_NOTE[0], starts[3], prefix=True)
    note_to = next(
        (i for i in range(note_from, note_from + 8) if lines[i].strip().endswith(LATER_NOTE[1])),
        None,
    )
    if note_to is None or note_to > starts[4]:
        raise CommandError("the later printing's Sermon IV note changed.")
    lines = _cut(lines, note_from, note_to + 1, [""])

    # Sermon I's passages set in columns, transcribed.
    for span, sentinel, _ in _SPLICES:
        t_from = _find(lines, span[0], starts[0])
        t_to = _find(lines, span[1], t_from)
        if t_to > starts[1]:
            raise CommandError(f"{span[0]!r} is not in Sermon I — the scan changed.")
        lines = _cut(lines, t_from, t_to, ["", sentinel, ""])

    starts = _openings(lines)
    end = _find(lines, LAST_LINE, starts[-1]) + 1
    out, dropped = [], []
    for n, ((title, heading), first) in enumerate(zip(CHAPTERS, starts, strict=True), start=1):
        last = starts[n] if n < len(starts) else end
        body = _chapter_body(lines[first + len(heading):last], n, heads, dropped)
        out.append((title, body))
    return out, dropped


class Command(BaseCommand):
    help = "Build Bosworth's Christ the Healer (1924) from the Archive scan (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        chapters, dropped = build_chapters(fetch_text(ARCHIVE_ID), fetch_text(WITNESS_ID))
        for text in dropped:
            self.stdout.write(f"  (dropped pencil note: {text!r})")

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 1000:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:60]:60} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
