"""Regenerate docs/tts-three-engines.pdf, the two-page TTS three-engine note.

    pip install reportlab && python3 docs/build-tts-three-engines-pdf.py

It is a black-and-white companion to tts-strategy.pdf: one strategy for
pre-rendering the whole library with Kokoro, Azure Neural TTS and Sunbird.
Corpus figures were measured from backend/library/fixtures/content (book and
sermon text, tags stripped) and are not recomputed here. Vendor prices and
licences come from web search in October 2026; check them before changing.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = str(Path(__file__).resolve().parent / "tts-three-engines.pdf")

BLACK = colors.black
GREY = colors.HexColor("#555555")
RULE = colors.HexColor("#999999")
BAND = colors.HexColor("#eeeeee")


def S(name, **kw):
    return ParagraphStyle(name, **kw)


BODY = S("body", fontName="Times-Roman", fontSize=9.4, leading=12.2,
         alignment=TA_JUSTIFY, textColor=BLACK, spaceAfter=5)
LEAD = S("lead", parent=BODY, fontSize=10.2, leading=13.6, spaceAfter=6)
H1 = S("h1", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=BLACK)
KICKER = S("kicker", fontName="Helvetica-Bold", fontSize=7.4, leading=10,
           textColor=GREY, spaceAfter=6)
H2 = S("h2", fontName="Helvetica-Bold", fontSize=10.2, leading=12.5,
       textColor=BLACK, spaceBefore=7, spaceAfter=3)
H3 = S("h3", fontName="Helvetica-Bold", fontSize=8.8, leading=11,
       textColor=BLACK, spaceBefore=1, spaceAfter=2)
BULLET = S("bullet", parent=BODY, leftIndent=11, bulletIndent=2, spaceAfter=2.5)
CELL = S("cell", fontName="Times-Roman", fontSize=8.1, leading=10, textColor=BLACK)
CELLB = S("cellb", parent=CELL, fontName="Times-Bold")
CELLH = S("cellh", fontName="Helvetica-Bold", fontSize=7.4, leading=9,
          textColor=BLACK)
BOX = S("box", parent=CELL, fontSize=8.4, leading=10.6)
FOOT = S("foot", fontName="Helvetica", fontSize=6.6, leading=8.4, textColor=GREY)


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(t, BULLET, bulletText="•") for t in items]


def table(rows, widths, bold_first_col=True, header=True):
    data = []
    for i, row in enumerate(rows):
        if header and i == 0:
            data.append([Paragraph(c, CELLH) for c in row])
        else:
            data.append([
                Paragraph(c, CELLB if (j == 0 and bold_first_col) else CELL)
                for j, c in enumerate(row)
            ])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, BLACK),
        ("LINEBELOW", (0, -1), (-1, -1), 0.9, BLACK),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), BAND),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.6, BLACK)]
    t.setStyle(TableStyle(style))
    return t


def engine_card(title, rows, width):
    """A boxed technology card: a title band, then label/value rows."""
    data = [[Paragraph(title, CELLH), ""]]
    for label, value in rows:
        data.append([Paragraph(label, CELLB), Paragraph(value, BOX)])
    t = Table(data, colWidths=[0.95 * inch, width - 0.95 * inch])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("BOX", (0, 0), (-1, -1), 0.8, BLACK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def pipeline(width):
    """The render pipeline as a row of boxed steps joined by arrows."""
    steps = [
        ("1  Text", "Fixture rows: chapters, sermons, bios"),
        ("2  Split", "One clip per paragraph, as the reader shows it"),
        ("3  Key", "sha256(text + engine + voice + version)"),
        ("4  Route", "Language picks Kokoro, Azure or Sunbird"),
        ("5  Render", "MP3 + word-timing JSON per clip"),
        ("6  Publish", "Object storage + CDN; one manifest per chapter"),
        ("7  Play", "ListenBar plays files; browser voice if missing"),
    ]
    arrow = Paragraph("→", S("arr", fontName="Helvetica-Bold",
                                  fontSize=10, leading=12, alignment=1))
    cells, widths = [], []
    box_w = (width - 6 * 0.16 * inch) / 7
    for i, (head, body) in enumerate(steps):
        cells.append([Paragraph(head, CELLH), Paragraph(body, S(
            "pb", parent=CELL, fontSize=7.4, leading=9))])
        widths.append(box_w)
        if i < len(steps) - 1:
            cells.append(arrow)
            widths.append(0.16 * inch)
    t = Table([cells], colWidths=widths)
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3),
             ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for c in range(0, len(cells), 2):
        style.append(("BOX", (c, 0), (c, 0), 0.8, BLACK))
    t.setStyle(TableStyle(style))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(GREY)
    canvas.drawString(doc.leftMargin, 0.45 * inch,
                      "Ochorus  ·  Audio for every language  ·  October 2026")
    canvas.drawRightString(LETTER[0] - doc.rightMargin, 0.45 * inch,
                           f"{doc.page} / 2")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 0.58 * inch,
                LETTER[0] - doc.rightMargin, 0.58 * inch)
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(
        OUT, pagesize=LETTER,
        leftMargin=0.62 * inch, rightMargin=0.62 * inch,
        topMargin=0.55 * inch, bottomMargin=0.72 * inch,
        title="Ochorus TTS: Three-Engine Strategy",
        author="Ochorus",
    )
    W = doc.width
    frame = Frame(doc.leftMargin, doc.bottomMargin, W, doc.height, id="f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])

    s = []

    # ---------------------------------------------------------------- page 1
    s.append(p("TEXT-TO-SPEECH  ·  STRATEGY, TECHNOLOGY AND APPROACH", KICKER))
    s.append(p("Audio for every language: three engines, rendered once", H1))
    s.append(Spacer(1, 6))
    s.append(p(
        "Ochorus should <b>pre-render the whole library as audio, once</b>, and "
        "serve it as plain files. No single text-to-speech system covers all ten "
        "of our languages under a licence that lets us publish the audio, so we "
        "use three: <b>Kokoro</b> (open, self-hosted) for English, Spanish, "
        "French, Portuguese and Hindi; <b>Azure Neural TTS</b> (paid, one-time) "
        "for Arabic, Ukrainian, Swahili and Amharic; and <b>Sunbird AI</b> "
        "(open, Ugandan) for Luganda. Estimated total: <b>about $650–850, "
        "paid once</b>, then about $1 a month for storage.", LEAD))

    s.append(p("1. Strategy", H2))
    s.append(p(
        "Speechify is ruled out: its terms do not allow audio generated for "
        "public distribution without a separate licence. That leaves three tests "
        "every option must pass, in this order:"))
    s += bullets([
        "<b>Language.</b> All ten languages must be covered. Luganda is the "
        "binding constraint: no commercial service we found supports it.",
        "<b>Licence.</b> We must be allowed to store the audio and serve it to "
        "anyone. This rules out Meta MMS-TTS (CC-BY-NC), Coqui XTTS "
        "(non-commercial), Speechify, and Piper's Swahili and Arabic voices.",
        "<b>Cost.</b> No bill that grows with readers. Rendering once and "
        "serving files makes the cost a fixed, one-time amount tied to the size "
        "of the library, not to how many people listen.",
    ])
    s.append(p(
        "Pre-rendering on a server also replaces the riskiest part of the "
        "earlier plan (<i>tts-plan.md</i>): running Kokoro inside the reader's "
        "browser, with an 80–160 MB download, iPhone memory limits and a "
        "device test matrix. A pre-rendered MP3 plays instantly on any phone, "
        "offline, and every chapter of a book sounds the same, as an audiobook "
        "should."))

    s.append(p("2. Which engine reads which language", H2))
    s.append(table([
        ["Language", "Text (M chars)", "Engine", "Why this engine"],
        ["English", "55.5", "Kokoro", "Best free quality; most of the library"],
        ["Spanish · French", "13.5 · 14.9", "Kokoro",
         "Supported natively; no cost"],
        ["Portuguese", "13.2", "Kokoro",
         "Brazilian voices; use Azure pt-PT if our text is European"],
        ["Hindi", "10.5", "Kokoro",
         "Supported; move to Azure if the listening test is weak"],
        ["Swahili", "21.6", "Azure",
         "Kenya + Tanzania voices; compare against Sunbird"],
        ["Arabic · Ukrainian", "7.0 · 5.9", "Azure",
         "Not in Kokoro; mature neural voices"],
        ["Amharic", "3.7", "Azure", "Only commercial engine we found with it"],
        ["Luganda", "6.5", "Sunbird", "Only usable option; needs native review"],
        ["<b>Total</b>", "<b>152.3</b>", "", "~107 Kokoro · ~38 Azure · ~6.5 Sunbird"],
    ], [1.25 * inch, 0.95 * inch, 0.75 * inch, W - 2.95 * inch]))

    s.append(p("3. The three technologies", H2))
    col = (W - 0.18 * inch) / 3
    cards = [
        engine_card("KOKORO-82M  ·  open model", [
            ("What", "82M-parameter neural TTS; 54 voices in 8 languages."),
            ("Licence", "Apache 2.0 weights. Audio is ours to publish."),
            ("Run it", "Batch job on a rented GPU via Kokoro-FastAPI "
             "(Docker, OpenAI-style API)."),
            ("Timings", "Word timestamps from the same call."),
            ("Watch", "Uses espeak-ng (GPL) for phonemes: fine for a "
             "batch tool we do not ship."),
        ], col),
        engine_card("AZURE NEURAL TTS  ·  cloud API", [
            ("What", "Microsoft's neural voices; 140+ locales incl. "
             "sw-KE, sw-TZ, am-ET, uk-UA, ar-*."),
            ("Licence", "Paid use; confirm terms allow storing and "
             "serving output publicly."),
            ("Run it", "Batch synthesis API from a Django management "
             "command; SSML for pauses."),
            ("Timings", "Word-boundary events give word timings."),
            ("Watch", "~$16 per 1M chars (HD ~$22). 500K free/month."),
        ], col),
        engine_card("SUNBIRD AI  ·  open model", [
            ("What", "Orpheus-3B fine-tune; 20 African languages "
             "incl. Luganda and Swahili."),
            ("Licence", "Apache 2.0, inheriting Meta's Llama 3 "
             "community licence."),
            ("Run it", "Self-hosted on a rented GPU; slower than "
             "Kokoro (3B params)."),
            ("Timings", "No word timings: align afterwards, or "
             "highlight per paragraph."),
            ("Watch", "Young model; a Luganda speaker must sign off."),
        ], col),
    ]
    s.append(Table([cards], colWidths=[col + 0.09 * inch, col + 0.09 * inch, col],
                   style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))

    s.append(PageBreak())

    # ---------------------------------------------------------------- page 2
    s.append(p("4. Approach: how the audio is made and played", H2))
    s.append(pipeline(W))
    s.append(Spacer(1, 5))
    s += bullets([
        "<b>One clip per paragraph.</b> It matches today's Listen mode "
        "(<i>listen.svelte.ts</i>): the same highlight, skip and resume, now "
        "with word-by-word highlighting where the engine gives timings.",
        "<b>Content-addressed files.</b> Each clip is named by a hash of its "
        "text, engine, voice and engine version. A corrected paragraph gets a "
        "new hash, so only that clip is re-rendered and paid for; unchanged "
        "clips are never touched. Modern English and young-reader editions are "
        "separate rows, so they get their own audio with no special case.",
        "<b>One render command, three back ends.</b> A management command "
        "(e.g. <i>render_audio --book &lt;slug&gt; --lang &lt;code&gt;</i>) "
        "routes each language to its engine, skips clips that already exist, "
        "and writes a chapter manifest listing clip URLs, durations and timings. "
        "New works are rendered as part of publishing, like PDF/EPUB exports.",
        "<b>Plain files, cheap hosting.</b> ~2,800 hours of audio is about "
        "40–60 GB of 32–48 kbps mono audio. Object storage with free "
        "egress (e.g. Cloudflare R2) costs about $1 a month.",
        "<b>Graceful fallback.</b> If a manifest or clip is missing, ListenBar "
        "falls back to the browser's own voices, exactly as today. Nothing "
        "breaks while the library is part-rendered.",
        "<b>Fixed voice per language.</b> One house voice per language (and "
        "optionally a second) keeps a book consistent. Readers keep speed "
        "control; voice choice remains available through browser voices.",
    ])

    s.append(p("5. Cost (one-time, at list prices)", H2))
    s.append(table([
        ["Engine", "Text", "How it is paid", "Estimate"],
        ["Kokoro", "~107M chars (~2,000 h audio)",
         "Rented GPU; runs far faster than real time", "$20–60"],
        ["Azure Neural", "~38M chars", "$16 per 1M characters", "~$610"],
        ["Sunbird", "~6.5M chars (~120 h audio)",
         "Rented GPU; a 3B model, much slower", "$30–150"],
        ["Storage + CDN", "40–60 GB", "Object storage, free egress", "~$1 / month"],
        ["<b>Total</b>", "", "",
         "<b>~$650–850 once</b>"],
    ], [1.05 * inch, 1.75 * inch, W - 3.9 * inch, 1.1 * inch]))
    s.append(p(
        "Contingencies: moving Hindi to Azure adds ~$170; European Portuguese "
        "via Azure adds ~$210. A single-vendor option (Azure for everything but "
        "Luganda) costs about $2,300.", S("note", parent=BODY, fontSize=8.6,
                                          leading=11, textColor=GREY, spaceBefore=4)))

    s.append(p("6. Rollout", H2))
    s.append(table([
        ["Phase", "What happens", "Done when"],
        ["0  Prove it", "Render two passages per language on each candidate "
         "engine; native speakers rate them blind. Confirm Azure and Llama 3 "
         "licence terms.", "An engine is chosen per language, in writing"],
        ["1  Pilot", "Build the render command, manifest and player support; "
         "render three flagship English books with Kokoro.",
         "Pilot books play on iPhone, Android and desktop"],
        ["2  Kokoro", "Render all English, Spanish, French, Portuguese, Hindi.",
         "~70% of the library has audio"],
        ["3  Azure", "Render Arabic, Ukrainian, Swahili, Amharic.",
         "Nine of ten languages covered"],
        ["4  Sunbird", "Render Luganda; a native reviewer checks samples from "
         "every book.", "All ten languages covered"],
        ["5  Ongoing", "New and corrected works render on publish.",
         "No chapter without audio"],
    ], [0.85 * inch, W - 2.85 * inch, 2.0 * inch]))

    s.append(p("7. Risks and how we handle them", H2))
    s.append(table([
        ["Risk", "Mitigation"],
        ["A voice mispronounces names and Scripture",
         "Pronunciation list per language (SSML / phoneme overrides); spot-check "
         "every book's first chapter"],
        ["Licence terms change or are stricter than reported",
         "Phase 0 gate; clips are tagged by engine, so one engine's audio can be "
         "re-rendered elsewhere"],
        ["Luganda quality is not good enough",
         "Ship Luganda on browser voices until a native reviewer approves"],
        ["Audio drifts from corrected text",
         "Content hashes: any text change re-renders that clip automatically"],
    ], [2.3 * inch, W - 2.3 * inch]))

    s.append(Spacer(1, 6))
    s.append(KeepTogether([p(
        "Sources (October 2026): Azure Speech language support and pricing; "
        "Kokoro-82M model card and Kokoro-FastAPI; Sunbird Orpheus-3B multilingual "
        "TTS model card and Sunflower v2 announcement; Speechify AI Voice API terms; "
        "Meta MMS-TTS and Piper voice model cards. Prices and licences were "
        "gathered by web search and must be confirmed with each vendor before "
        "purchase. Corpus sizes measured from the Ochorus content fixture.", FOOT)]))

    doc.build(s)


if __name__ == "__main__":
    build()
    print(OUT)
