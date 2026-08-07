"""Regenerate docs/tts-strategy.pdf.

    pip install reportlab && python3 docs/build-tts-strategy-pdf.py

The PDF is committed because it is the artefact people read; this script is
committed so the artefact stays editable. Corpus figures quoted in §2 and §8
were measured from backend/library/fixtures/content and are not recomputed
here — re-measure before changing them.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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

OUT = str(Path(__file__).resolve().parent / "tts-strategy.pdf")

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5a5a5a")
ACCENT = colors.HexColor("#7a4b2a")
RULE = colors.HexColor("#d8d2c8")
BAND = colors.HexColor("#f4f1ec")

ss = getSampleStyleSheet()


def S(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


BODY = S("body", fontName="Times-Roman", fontSize=9.6, leading=13.4,
         alignment=TA_JUSTIFY, textColor=INK, spaceAfter=7)
LEAD = S("lead", parent=BODY, fontSize=10.6, leading=15, spaceAfter=9)
H1 = S("h1", fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=INK,
       spaceAfter=2, spaceBefore=0)
KICKER = S("kicker", fontName="Helvetica-Bold", fontSize=7.6, leading=10,
           textColor=ACCENT, spaceAfter=8)
H2 = S("h2", fontName="Helvetica-Bold", fontSize=10.4, leading=13, textColor=ACCENT,
       spaceBefore=10, spaceAfter=4)
H3 = S("h3", fontName="Helvetica-BoldOblique", fontSize=9.4, leading=12,
       textColor=INK, spaceBefore=7, spaceAfter=2)
BULLET = S("bullet", parent=BODY, leftIndent=13, bulletIndent=3, spaceAfter=4)
CELL = S("cell", fontName="Times-Roman", fontSize=8.2, leading=10.4, textColor=INK)
CELLB = S("cellb", parent=CELL, fontName="Times-Bold")
CELLH = S("cellh", fontName="Helvetica-Bold", fontSize=7.6, leading=9.6,
          textColor=colors.white)
NOTE = S("note", parent=BODY, fontSize=8.4, leading=11.2, textColor=MUTED,
         spaceAfter=5)
CAP = S("cap", fontName="Helvetica-Oblique", fontSize=7.6, leading=10,
        textColor=MUTED, spaceAfter=8)

story = []


def para(t, s=BODY):
    story.append(Paragraph(t, s))


def bullets(items, style=BULLET):
    for it in items:
        story.append(Paragraph(it, style, bulletText="•"))


def gap(h=6):
    story.append(Spacer(1, h))


def page(kicker, title):
    story.append(Paragraph(kicker, KICKER))
    story.append(Paragraph(title, H1))
    story.append(Spacer(1, 1))
    story.append(_rule())
    story.append(Spacer(1, 8))


def _rule():
    t = Table([[""]], colWidths=[6.9 * inch], rowHeights=[1.6])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    return t


def table(rows, widths, header=True, align=None, zebra=True):
    data = []
    for i, r in enumerate(rows):
        style = CELLH if (header and i == 0) else CELL
        data.append([Paragraph(str(c), style) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if (i - (1 if header else 0)) % 2 == 1:
                cmds.append(("BACKGROUND", (0, i), (-1, i), BAND))
    t.setStyle(TableStyle(cmds))
    return t


def callout(title, body):
    inner = [
        [Paragraph(title, S("ct", fontName="Helvetica-Bold", fontSize=8.4,
                            leading=11, textColor=ACCENT))],
        [Paragraph(body, S("cb", parent=BODY, fontSize=8.6, leading=11.6,
                           spaceAfter=0))],
    ]
    t = Table(inner, colWidths=[6.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
    ]))
    return t


# ============================================================ page 1
story.append(Spacer(1, 10))
story.append(Paragraph("OCHORUS &nbsp;&middot;&nbsp; TAKE ROOT &nbsp;&middot;&nbsp; EVERY TONGUE",
                       S("cover_k", fontName="Helvetica-Bold", fontSize=8.4,
                         leading=12, textColor=ACCENT, spaceAfter=10)))
story.append(Paragraph("Building the best free<br/>text-to-speech system",
                       S("cover_t", fontName="Helvetica-Bold", fontSize=24,
                         leading=28, textColor=INK, spaceAfter=8)))
story.append(Paragraph(
    "A plan for giving every book, sermon and verse we publish a natural "
    "spoken voice &mdash; in every language we serve, at a cost that stays "
    "near zero as the library grows.",
    S("cover_s", parent=LEAD, fontSize=11.4, leading=16, textColor=MUTED,
      alignment=0, spaceAfter=13)))
story.append(_rule())
gap(10)

story.append(Paragraph("Executive summary", H2))
para(
    "Ochorus already speaks. Every chapter has a <i>Listen</i> mode that reads "
    "the text aloud using the voices built into the reader's own device. It "
    "costs nothing to run, works offline, and needs no audio files. For English "
    "and Spanish it is genuinely good. For Luganda it produces nothing at all, "
    "and for Swahili it produces something most listeners will switch off "
    "within a minute.")
para(
    "That gap is the whole problem. The languages where a spoken edition would "
    "matter most &mdash; where oral transmission is the norm, where literacy "
    "rates are lower, where a shared phone is the only device &mdash; are "
    "precisely the languages the device voices do not cover. We are strongest "
    "where we are least needed.")
para(
    "Closing it does not require becoming an audio company. The central move is "
    "simple: <b>our text does not change, so we should not be synthesising it "
    "over and over.</b> Unlike a chatbot, we know every sentence we will ever "
    "need to speak, in advance &mdash; which converts a per-request GPU problem "
    "into a one-time batch render plus the cost of serving static files.")

para(
    "There is already a plan for part of this. <font face='Times-Bold'>"
    "docs/tts-plan.md</font> commits to running neural TTS <i>in the browser</i> "
    "&mdash; Kokoro or Piper via ONNX, model cached on the device &mdash; and "
    "its first phase has partly shipped. That plan is sound and this document "
    "does not replace it. But it makes one explicit concession: Swahili and "
    "Luganda fall back to device voices, &ldquo;since quality neural voices for "
    "Luganda don't exist&rdquo;. That concession is the gap, and §5 argues the "
    "two approaches are complementary rather than competing.")

gap(4)
story.append(callout(
    "The recommendation in one paragraph",
    "Continue the in-browser neural work for the languages it can serve. "
    "Alongside it, promote pre-rendered audio from an optional Phase 2 nicety "
    "to the primary answer for languages the device and in-browser tiers cannot "
    "reach: render the fixed corpus once with an open-licence engine, store it "
    "as Opus on the CDN, and serve it as static files. Then do the expensive "
    "thing the existing plan stops short of &mdash; build a Luganda voice, from "
    "speech recorded with native speakers. One pipeline, three consumers."))
gap(8)

story.append(Paragraph("What follows", H2))
story.append(table([
    ["§", "Section", "The question it answers"],
    ["2", "Where we are today", "What the current Listen mode does, and exactly where it fails"],
    ["3", "The real problem", "Why low-resource languages are a different engineering problem"],
    ["4", "Technology landscape", "Which engines are actually usable, and under which licences"],
    ["5", "Architecture", "In-browser neural vs pre-rendered, and why both are needed"],
    ["6", "Getting voices", "How to obtain a voice for a language that has none"],
    ["7", "Scripture is different", "What Take Root needs that a book reader does not"],
    ["8", "What it costs", "Compute, storage and bandwidth, with the corpus measured"],
    ["9", "Roadmap", "How this extends the phases already in docs/tts-plan.md"],
    ["10", "Risks and decisions", "What could go wrong, and what we need to decide"],
], [0.32 * inch, 1.75 * inch, 4.83 * inch]))

story.append(PageBreak())

# ============================================================ page 2
page("SECTION 2", "Where we are today")
para(
    "The reader's Listen mode is implemented entirely in the browser. It holds "
    "the chapter as a list of paragraphs and speaks them one at a time through "
    "the Web Speech API, using whichever voices the operating system already "
    "provides. There is no server, no audio file and no network request "
    "involved in playback. Work is in flight: Listen has reached author "
    "biographies, and the voice and speed picker with preview has shipped.", LEAD)

story.append(Paragraph("What the current implementation gets right", H2))
bullets([
    "<b>One utterance per paragraph, not one per chapter.</b> This gives exact "
    "paragraph boundaries for highlight-as-you-listen, lets a speed or voice "
    "change take effect immediately by restarting only the current paragraph, "
    "and avoids the long-standing stall Chrome exhibits on long utterances.",
    "<b>Genuinely free and genuinely offline.</b> No per-character billing, no "
    "API key, no bandwidth. A reader on a metered connection pays nothing to "
    "listen to a book they have already downloaded.",
    "<b>Five playback speeds, a sleep timer, and Media Session integration</b> "
    "&mdash; so lock-screen controls and headphone buttons work, and the phone "
    "can go dark in a listener's pocket.",
    "<b>Preferences persist</b> (speed and chosen voice), and the code holds a "
    "reference to the active utterance to work around Chrome's habit of "
    "garbage-collecting it mid-sentence and never firing the callback that "
    "advances to the next paragraph.",
])

story.append(Paragraph("Where it fails", H2))
para(
    "Every one of those strengths depends on a voice existing on the listener's "
    "device. When one does not, the interface has exactly one thing to say, and "
    "it already says it: <i>&ldquo;No voices for this language on this "
    "device.&rdquo;</i> That string is the honest admission at the centre of "
    "this document.")

story.append(table([
    ["Language", "Device voice availability", "Practical quality today"],
    ["English", "Universal, many voices, often neural", "Good to very good"],
    ["Spanish", "Universal, several regional variants", "Good"],
    ["Portuguese", "Universal, pt-BR and pt-PT", "Good"],
    ["Hindi", "Widely present on Android and iOS", "Acceptable to good"],
    ["Arabic", "Present, but variable; diacritics ignored", "Mixed &mdash; see §7"],
    ["Ukrainian", "Present on recent Android and iOS; absent on older devices", "Acceptable"],
    ["Swahili", "Sometimes present on Android; rarely elsewhere", "Poor &mdash; often mispronounced or absent"],
    ["Luganda", "Effectively nowhere", "<b>Nothing plays at all</b>"],
], [0.95 * inch, 2.85 * inch, 3.1 * inch]))
story.append(Paragraph(
    "Availability is a property of the reader's device, not of our software, so "
    "it also varies with OS version, region and whether the user has downloaded "
    "optional voice packs. Two readers in the same city can get different results.",
    CAP))

story.append(Paragraph("The other failure is silent", H2))
para(
    "Even where a voice exists, it is a general-purpose one. It reads "
    "&ldquo;Ps. 119:105&rdquo; as letters and digits. It does not know that "
    "&ldquo;Zerubbabel&rdquo;, &ldquo;Gethsemane&rdquo; or "
    "&ldquo;Chrysostom&rdquo; are names. It cannot tell a scripture quotation "
    "from the author's own sentence, so a passage that the eye reads as quoted "
    "arrives in the ear as continuous prose. In devotional writing, where "
    "quotation is half the text, that flattening is a real loss of meaning.")

gap(2)
story.append(callout(
    "The measured corpus",
    "The library today holds <b>2,414 chapters and sermons</b> across seven "
    "languages, totalling roughly <b>6.2 million words</b>. At a normal reading "
    "pace that is about <b>685 hours</b> of speech &mdash; 463 of them in "
    "English. This is a large number for a person and a small number for a "
    "computer, and that asymmetry is the basis of the plan in §5."))

story.append(PageBreak())

# ============================================================ page 3
page("SECTION 3", "The real problem: low-resource languages")
para(
    "It is tempting to treat this as one problem with one solution &mdash; "
    "&ldquo;add better TTS&rdquo;. It is two problems, and they have almost "
    "nothing in common.", LEAD)

story.append(table([
    ["", "Well-served languages", "Low-resource languages"],
    ["Examples in our set", "en, es, pt, hi", "sw, lg (and every language we add next)"],
    ["What exists", "Multiple good voices, already on the device", "No device voice; few or no open models"],
    ["The problem is", "Polish &mdash; pronunciation of names, quotation prosody, reference expansion",
     "Existence &mdash; there is nothing to polish"],
    ["Cost of solving", "Low; incremental improvements to what ships today",
     "High; requires obtaining audio and training a voice"],
    ["Who can judge it", "Anyone", "Only a native speaker"],
    ["Failure if ignored", "Slightly stiff listening", "An entire language has no audio edition"],
], [1.1 * inch, 2.6 * inch, 3.2 * inch]))
gap(6)

story.append(Paragraph("Why the second column is hard", H2))
para(
    "Modern neural TTS is trained on recorded speech paired with transcripts. "
    "For English, tens of thousands of hours are publicly available. For "
    "Luganda, the openly-licensed, studio-quality, single-speaker recordings "
    "that a high-quality voice normally requires do not meaningfully exist. "
    "Multilingual research models cover Luganda &mdash; Meta's MMS project "
    "covers over a thousand languages &mdash; but coverage and quality are not "
    "the same thing, and as §4 shows, the licence on the broadest of those "
    "models forbids commercial use in a way that matters even for a free "
    "product.")
para(
    "There is also a subtler trap. A model can be intelligible and still be "
    "wrong in ways only a speaker hears: Luganda and Swahili are tonal or "
    "tone-influenced, Luganda has phonemic vowel and consonant length, and "
    "getting these wrong changes meaning rather than merely sounding foreign. "
    "A synthetic voice that mangles them is not a rough draft of a good voice. "
    "It is a liability, especially when the text is Scripture.")

gap(2)
story.append(callout(
    "The governing principle, carried over from translation",
    "We already refuse to present an unreviewed AI translation as though it "
    "were an original &mdash; it wears a badge until a native speaker approves "
    "it. Synthetic audio deserves exactly the same treatment. A generated voice "
    "in a language no reviewer has signed off on should be labelled as "
    "synthetic and unreviewed, and a listener should be able to tell, before "
    "pressing play, whether they are hearing a checked voice or a machine's "
    "best guess."))
gap(6)

story.append(Paragraph("What this implies for sequencing", H2))
para(
    "The two columns want opposite orderings. The well-served languages are "
    "cheap to improve and cover most of our current readership, so they are "
    "tempting to do first. The low-resource languages are where the product is "
    "actually broken. The roadmap in §9 resolves this by making the first "
    "phase infrastructure that serves both, then spending the expensive effort "
    "on Luganda and Swahili before returning to polish.")

story.append(PageBreak())

# ============================================================ page 4
page("SECTION 4", "Technology landscape")
para(
    "&ldquo;Free&rdquo; has two meanings here and both matter: free for the "
    "listener at runtime, and free of licence terms that would restrict a "
    "public-domain library. We already prefer public-domain Bible texts "
    "specifically so that a quotation carries no attribution obligation; the "
    "same discipline should govern the voice that speaks them.", LEAD)

story.append(table([
    ["Engine", "Licence", "Strengths", "Weaknesses / notes"],
    ["<b>Piper</b>", "MIT",
     "Fast enough to run on a Raspberry Pi; dozens of languages; trains a new "
     "voice from modest data; ONNX runtime",
     "Quality is good, not state-of-the-art. The natural default for "
     "pre-rendering and for languages we train ourselves."],
    ["<b>Kokoro</b>", "Apache-2.0",
     "Very high quality for its size (~82M parameters); permissive; runs on CPU",
     "Limited language coverage; not a path to Luganda without training work."],
    ["<b>Meta MMS-TTS</b>", "CC-BY-NC-4.0",
     "Covers 1,100+ languages including Luganda and Swahili &mdash; by far the "
     "broadest coverage available",
     "<b>Non-commercial licence.</b> Needs legal review before any use, and is "
     "a poor foundation to build a decade on."],
    ["<b>StyleTTS2</b>", "MIT",
     "Human-parity quality on English benchmarks; expressive prosody control",
     "Heavier to run; training a new language is a research project, not a "
     "configuration change."],
    ["<b>Coqui XTTS</b>", "CPML (restricted)",
     "Voice cloning from seconds of audio; strong multilingual",
     "Licence restricts commercial use; upstream company wound down. Avoid as "
     "a dependency."],
    ["<b>espeak-ng</b>", "GPL-3.0",
     "Formant synthesis; supports 100+ languages including Luganda; tiny; "
     "totally deterministic",
     "Sounds robotic. Genuinely useful as a <i>phonemizer</i> feeding a neural "
     "model, and as a last-resort fallback."],
    ["<b>Cloud APIs</b> (Google, Azure, ElevenLabs)", "Commercial, metered",
     "Best quality; no infrastructure to run",
     "Per-character billing forever; coverage of Luganda is thin to absent; "
     "creates a dependency we cannot promise to keep free."],
], [0.92 * inch, 1.0 * inch, 2.28 * inch, 2.7 * inch]))
gap(6)

story.append(Paragraph("Reading the table", H2))
bullets([
    "<b>Piper is the workhorse.</b> MIT, mature, trainable on the amount of "
    "audio we could realistically collect, and cheap enough that rendering the "
    "entire corpus is an afternoon rather than a budget line.",
    "<b>Kokoro is the quality upgrade</b> for the languages it covers, and can "
    "be swapped in per-language later without changing the architecture, "
    "because a pre-render pipeline does not care which engine produced the file.",
    "<b>MMS is the tempting shortcut and should be treated carefully.</b> It is "
    "the only off-the-shelf answer for Luganda, and its licence is "
    "non-commercial. Even for a free product, building the permanent audio "
    "layer of three properties on a CC-BY-NC model is a decision to make "
    "deliberately, with advice, not by default.",
    "<b>Cloud APIs are the wrong shape.</b> Not because they are bad &mdash; "
    "they are the best-sounding option &mdash; but because a metered "
    "per-character cost scales with listening, and the entire promise here is "
    "that listening is free.",
])

story.append(Paragraph("One non-obvious component", H2))
para(
    "Whatever engine we choose, we will need a <b>pronunciation lexicon</b>: an "
    "explicit mapping from the proper nouns of Scripture and church history to "
    "their phonemes, per language. This is not glamorous and it is the single "
    "highest-leverage quality improvement available, because biblical names are "
    "exactly the words a general-purpose model has never seen and exactly the "
    "words our text is full of. It is also portable &mdash; the same lexicon "
    "improves every engine we ever use.")

story.append(PageBreak())

# ============================================================ page 5
page("SECTION 5", "Architecture: two paths, and why we need both")
para(
    "The existing plan and this one agree on the goal and differ on <i>where "
    "synthesis happens</i>. That resolves cleanly once you notice the two "
    "approaches fail in opposite places.", LEAD)

story.append(table([
    ["", "<b>In-browser neural</b> (committed plan)", "<b>Pre-rendered</b> (this proposal)"],
    ["Synthesis runs", "On the listener's device, via ONNX + WebGPU/WASM",
     "Once, on our machines, as a batch job"],
    ["Delivery", "An 80&ndash;120 MB model, downloaded once and cached",
     "Opus audio per chapter, served from the CDN"],
    ["Server cost", "Zero", "Storage and bandwidth only"],
    ["Works on a cheap phone",
     "Needs WebGPU or a fast WASM path and ~500 MB peak memory &mdash; "
     "uncertain, and exactly what the spike must answer",
     "Yes, unconditionally; it only has to play an audio file"],
    ["New language requires", "A model that exists and ships to every device",
     "A model that exists on <i>one</i> machine, once"],
    ["Can it be reviewed?", "No &mdash; output differs per device and per run",
     "Yes &mdash; a file can be listened to and approved"],
    ["<b>Luganda</b>", "<b>Cannot help</b>; the plan falls back to device voices",
     "<b>Can</b>, if we build the voice"],
], [1.12 * inch, 2.85 * inch, 2.93 * inch]))
gap(5)
story.append(callout(
    "The reconciliation",
    "In-browser neural is a <i>quality</i> upgrade for languages that already "
    "have a model and devices that can run it. Pre-rendering is an "
    "<i>availability</i> mechanism for everything else. The committed plan "
    "already contains pre-rendering &mdash; as an optional Phase 2 item, "
    "&ldquo;flagship audio for top-N books&rdquo;. The argument here is only "
    "that for sw and lg it is not optional and not Phase 2: it is the only "
    "thing that works."))
gap(7)

story.append(Paragraph("Three tiers, chosen per language", H2))
story.append(table([
    ["Tier", "What it is", "When it is used"],
    ["<b>0 &mdash; Device</b>", "Web Speech, unchanged",
     "Wherever the device has a good voice; always offline"],
    ["<b>1 &mdash; In-browser neural</b>", "Kokoro or Piper via ONNX",
     "Opt-in HD, where a model exists and the device can run it"],
    ["<b>2 &mdash; Pre-rendered</b>", "Opus per chapter + timing map",
     "Languages tiers 0 and 1 cannot serve; offline; Take Root verses"],
], [1.3 * inch, 1.95 * inch, 3.65 * inch]))
gap(4)

story.append(Paragraph("The pipeline", H2))
para(
    "Five batch steps, slotting behind the <font face='Times-Bold'>TtsBackend"
    "</font> interface the committed plan already defines: pre-rendered audio "
    "is simply another backend.")
story.append(table([
    ["Step", "What happens", "Why it matters"],
    ["1. Segment",
     "Split the chapter HTML into speech units, keeping paragraph boundaries "
     "and marking quotations and verse references",
     "The paragraph is already the unit of the reader's highlight logic, so "
     "the front end barely changes"],
    ["2. Normalise",
     "Expand references and numerals to speakable words; apply the "
     "pronunciation lexicon",
     "Where quality is won or lost, and it is language-specific"],
    ["3. Synthesise",
     "Render each unit with the language's chosen engine and voice",
     "Batch and parallel &mdash; no user is waiting"],
    ["4. Assemble",
     "Concatenate to one Opus file per chapter plus a timing map of paragraph "
     "start times",
     "One request per chapter; the timing map drives highlighting just as the "
     "per-paragraph callbacks do today"],
    ["5. Publish",
     "Upload behind the CDN; record voice, engine version and review state "
     "against the chapter",
     "Provenance lets us re-render only what changed, and lets the UI badge an "
     "unreviewed voice"],
], [0.85 * inch, 2.95 * inch, 3.1 * inch]))

story.append(PageBreak())

# ============================================================ page 6
page("SECTION 6", "Getting a voice where none exists")
para(
    "For Luganda, and for most languages we will add after it, no acceptable "
    "open voice exists. This section is about manufacturing one. It is the "
    "expensive part of the plan and the part that cannot be rushed.", LEAD)

story.append(Paragraph("What a trainable voice actually requires", H2))
story.append(table([
    ["Ingredient", "Realistic target", "Notes"],
    ["Recorded speech", "5&ndash;10 hours from one speaker; 1&ndash;2 hours can "
     "produce a usable voice by fine-tuning a multilingual base",
     "Single speaker, consistent microphone, quiet room. Consistency matters "
     "more than studio equipment."],
    ["Transcripts", "Exact, verified, matching the audio word for word",
     "We have an advantage here: we can supply the script from our own "
     "public-domain corpus, so the text is already clean and already licensed."],
    ["A phonemizer", "espeak-ng already supports Luganda and Swahili",
     "Converts text to phonemes so the model learns sound, not spelling."],
    ["A speaker", "A native speaker willing to be the voice of the library",
     "This is a relationship, not a procurement. Consent must be explicit, "
     "written, and specific about permanence and scope."],
    ["A reviewer", "A second native speaker to judge the output",
     "The person who records should not be the only person who approves."],
], [0.95 * inch, 2.35 * inch, 3.6 * inch]))
gap(6)

story.append(Paragraph("Three routes, in order of preference", H2))
bullets([
    "<b>Record our own.</b> Highest quality, clearest licensing, and it "
    "produces something reusable: an openly-licensed Luganda speech dataset "
    "that did not previously exist, which others can use. The cost is "
    "coordination and a few weeks of a speaker's time. Recording our own "
    "public-domain text sidesteps every rights question about the script.",
    "<b>Fine-tune an existing multilingual model</b> on a smaller amount of "
    "recorded audio. Faster and cheaper, but the licence of the base model "
    "propagates to the result &mdash; which is exactly the reason to avoid a "
    "non-commercial base.",
    "<b>Use existing open corpora</b> (Common Voice, OpenSLR and similar) where "
    "they cover the language. Cheapest, but coverage for Luganda is thin, and "
    "crowd-sourced recordings are many speakers in many rooms, which suits "
    "speech <i>recognition</i> far better than speech synthesis.",
])

story.append(Paragraph("The ethical frame, stated plainly", H2))
para(
    "A synthetic voice is a person's voice. Anyone who records for us should "
    "know, in their own language and in writing, what the recording will be "
    "used for, that the resulting voice can say sentences they never spoke, "
    "that it will be published freely, and how to ask for it to be withdrawn. "
    "They should be credited unless they ask not to be, and paid if they want "
    "to be paid. None of this is legally forced on us; all of it is the "
    "difference between a gift and an extraction.")
para(
    "The same care applies to whose voice we do <i>not</i> use. No cloning a "
    "preacher's voice from sermon recordings, however technically easy and "
    "however public-domain the text. A voice is not in the public domain "
    "because the words are.")

story.append(PageBreak())

# ============================================================ page 7
page("SECTION 7", "Scripture is different: what Take Root needs")
para(
    "A Bible API has requirements a book reader does not, and they are "
    "specific enough to design for rather than discover later.", LEAD)

story.append(table([
    ["Requirement", "Why it exists", "Design consequence"],
    ["<b>Verse-addressable audio</b>",
     "Callers ask for John 3:16&ndash;18, not for a chapter. Any range must be "
     "playable.",
     "Render per verse and store per-verse timings; assemble ranges by "
     "concatenation or by byte-range within a chapter file. Never re-synthesise "
     "per request."],
    ["<b>Verse numbers are optional</b>",
     "Spoken aloud, &ldquo;sixteen&rdquo; between sentences is an "
     "interruption; for study it is essential.",
     "Store number announcements as separate, skippable units so both modes "
     "come from one render."],
    ["<b>Absolute textual fidelity</b>",
     "Scripture wording must come from the trusted Bible text, never from a "
     "model's memory or paraphrase.",
     "The normalisation step may change <i>how a word is pronounced</i>. It "
     "may never change <i>which words are spoken</i>. This should be enforced "
     "by a test, not by discipline."],
    ["<b>A proper-noun lexicon per language</b>",
     "Biblical names are the highest-frequency out-of-vocabulary words in the "
     "entire text.",
     "Build it once per language, version it, and share it with Ochorus &mdash; "
     "the same names appear in every devotional we publish."],
    ["<b>Per-translation rendering</b>",
     "Each language has its own authoritative text (Reina-Valera 1858, Van "
     "Dyck, Kulish, and so on).",
     "Audio is keyed by translation code, not by language. Two Spanish "
     "translations are two renders."],
    ["<b>Reverence in prosody</b>",
     "Scripture read at the pace and pitch of a news bulletin sounds wrong to "
     "the people who care most about it.",
     "Slower default rate, longer inter-verse pauses, and native-speaker review "
     "as an acceptance criterion rather than a nicety."],
], [1.2 * inch, 2.6 * inch, 3.1 * inch]))
gap(6)

story.append(Paragraph("Why this belongs in Take Root rather than in each app", H2))
para(
    "Ochorus quotes Scripture constantly, in every language, and already "
    "sources that wording from Take Root rather than from any model. If Take "
    "Root serves the audio for a verse as well as its text, then a quotation "
    "inside a devotional can be spoken in the same voice, from the same trusted "
    "text, as the same verse read in the Bible reader. Building the audio layer "
    "anywhere else guarantees two renderings of the same verse that drift apart.")

gap(2)
story.append(callout(
    "A concrete scale check",
    "A complete Bible read aloud is roughly 75 hours. Across the eight "
    "languages we currently target that is about 600 hours of audio &mdash; "
    "comparable to the 685 hours already implied by the Ochorus library, and "
    "equally a one-time cost. At Opus bitrates suitable for speech, a whole "
    "Bible is on the order of 1&ndash;2 GB per translation."))

story.append(PageBreak())

# ============================================================ page 8
page("SECTION 8", "What it costs")
para(
    "The numbers below use the measured corpus: 2,414 chapters and sermons, "
    "6.2 million words, about 685 hours of speech at a normal reading pace. "
    "They are order-of-magnitude estimates intended to establish whether this "
    "is a hundred-dollar problem or a hundred-thousand-dollar one.", LEAD)

story.append(table([
    ["Line item", "Estimate", "Basis"],
    ["<b>One-time render of the whole library</b>",
     "Tens of dollars of compute",
     "Piper synthesises far faster than real time on commodity CPU; 685 hours "
     "of audio is a batch job measured in CPU-hours, parallelised across cheap "
     "workers."],
    ["<b>Storage</b>",
     "~30 GB for the library; ~1&ndash;2 GB per Bible translation",
     "Opus at speech-appropriate bitrates is roughly 0.5&ndash;1 MB per minute "
     "of speech at generous quality, less at conservative settings."],
    ["<b>Bandwidth</b>",
     "The only cost that scales with usage",
     "A chapter is a few megabytes. Public-domain audio never expires, so edge "
     "caching is near-total and origin egress stays small."],
    ["<b>Training one new voice</b>",
     "Low hundreds of dollars of GPU time, plus weeks of human coordination",
     "The compute is not the expensive part. Finding, recording and reviewing "
     "with a speaker is."],
    ["<b>Re-render after a text fix</b>",
     "Cents",
     "Only the changed chapters re-render, because provenance is recorded per "
     "chapter."],
    ["<b>On-demand tier</b>",
     "Small and bounded",
     "Serves only text with no pre-render yet; every request it answers becomes "
     "a cached file."],
], [1.55 * inch, 1.75 * inch, 3.6 * inch]))
gap(6)

story.append(Paragraph("The comparison that decides the architecture", H2))
para(
    "A commercial TTS API priced per character would charge for the same "
    "sentence every time anyone listened to it. Our corpus is 6.2 million "
    "words; at typical commercial rates a <i>single</i> full pass over it "
    "already runs into the hundreds of dollars, and every subsequent listener "
    "pays again. The pre-render approach pays once, in the tens of dollars, and "
    "then serves bytes. Ten thousand listeners cost the same to synthesise as "
    "one.")
para(
    "This is the entire economic argument, and it holds regardless of which "
    "engine wins the quality comparison. It is why the recommendation is a "
    "pipeline shape rather than a model choice: the shape is what makes free "
    "sustainable, and the model inside it can be replaced whenever something "
    "better appears.")

gap(2)
story.append(callout(
    "What is not in these numbers",
    "Human review time, which is the real budget. Someone has to listen to a "
    "Luganda chapter and say whether it is right. Estimating that in dollars "
    "misses the point &mdash; it is the same native-speaker review capacity "
    "that the translation work already needs, and it is the genuine constraint "
    "on how fast any of this ships."))

story.append(PageBreak())

# ============================================================ page 9
page("SECTION 9", "Roadmap")
para(
    "This extends the phases in <font face='Times-Bold'>docs/tts-plan.md</font> "
    "rather than replacing them. Phases 0 and 1 there stand as written; what "
    "follows adds a track beside them and then converges.", LEAD)

for title, sub, items in [
    ("Track A &mdash; Continue the committed plan, unchanged",
     "Phase 0 polish, then the spike, then in-browser neural",
     ["Finish Phase 0: engine-interface refactor, account-synced voice prefs, "
      "sentence-level boundary highlighting, auto-advance.",
      "Run the spike as specified; its answer determines how much Track B "
      "has to carry.",
      "Ship in-browser neural where the gates pass; opt-in elsewhere."]),
    ("Track B &mdash; Worth doing whatever the spike says",
     "Small, front-end, no new infrastructure, no dependency on Track A",
     ["Tell the reader the truth about voice availability <i>before</i> they "
      "press play, not after.",
      "Ship a pronunciation lexicon for biblical proper nouns; the same lexicon "
      "later feeds every engine.",
      "Expand references and numerals into speakable words at synthesis time, "
      "without touching the stored text.",
      "Instrument what people listen to, and in which languages."]),
    ("Phase 2&#8242; &mdash; Build the pre-render pipeline properly",
     "Promoting the committed plan's optional item to real infrastructure",
     ["Stand up the five-step pipeline of §5 as a batch job over the fixture "
      "content, behind the existing TtsBackend interface.",
      "Render English first &mdash; we can evaluate it ourselves and it "
      "exercises every part of the pipeline.",
      "Extend offline download to include a book's audio.",
      "Record engine, voice and version per chapter so re-rendering is "
      "incremental."]),
    ("Phase 3 &mdash; Close the low-resource gap",
     "The part the committed plan explicitly sets aside; the point of this document",
     ["Resolve the MMS licence question and choose the licence-safe engine path "
      "for Luganda and Swahili.",
      "Recruit and record native speakers; publish the resulting speech dataset "
      "openly if they consent.",
      "Train and evaluate with native reviewers, gated by the same approval "
      "discipline as translation &mdash; an unreviewed voice is badged, never "
      "presented as final.",
      "Render and ship the Luganda and Swahili libraries."]),
    ("Phase 4 &mdash; Scripture audio and the shared service",
     "Where the three properties converge",
     ["Extend the pipeline to verse granularity and render the Bible "
      "translations already configured per language.",
      "Serve verse-range audio from Take Root so a quotation in a devotional "
      "and the same verse in the Bible reader are one recording.",
      "Expose the pipeline as a shared service a third consumer can adopt."]),
]:
    block = [
        Paragraph(title, H2),
        Paragraph(sub, S("sub", parent=NOTE, fontName="Times-Italic", spaceAfter=3)),
    ]
    for it in items:
        block.append(Paragraph(it, BULLET, bulletText="•"))
    story.append(KeepTogether(block))

gap(4)
story.append(callout(
    "Sequencing note",
    "Track B is worth doing whatever else happens: it improves what ships today "
    "and produces the listening data the later phases depend on. Phase 3 is the "
    "one that must not be quietly dropped once Track A proves satisfying "
    "&mdash; the committed plan sets it aside, and that is the decision this "
    "document asks to revisit."))

story.append(PageBreak())

# ============================================================ page 10
page("SECTION 10", "Risks, open questions, decisions needed")

story.append(Paragraph("Risks", H2))
story.append(table([
    ["Risk", "Consequence", "Mitigation"],
    ["A non-commercial model licence becomes load-bearing",
     "The audio layer of three properties rests on terms we cannot honour",
     "Settle the MMS licence question before phase 3, not during it. Prefer MIT "
     "or Apache-licensed engines even at some quality cost."],
    ["Synthetic Scripture that mispronounces meaning-bearing tone or length",
     "Text that is doctrinally wrong to the ear while being correct on the page",
     "Native review as an acceptance gate, not a follow-up. Badge unreviewed "
     "voices exactly as unreviewed translations are badged."],
    ["Storage and bandwidth grow faster than expected",
     "A cost that was supposed to be near zero becomes a monthly line item",
     "Conservative Opus bitrates; aggressive edge caching; render on first "
     "demand rather than everything up front if usage data justifies it."],
    ["Speaker consent handled casually",
     "A person's voice used in ways they did not expect &mdash; a real harm and "
     "an irreversible one",
     "Written, specific, translated consent, with a withdrawal path, before any "
     "recording session."],
    ["The pipeline becomes a second content system",
     "Audio drifts out of step with corrected text",
     "Provenance per chapter and re-render on text change, driven by the same "
     "correction chain that already fixes bodies at deploy."],
    ["Effort concentrates on English because it is easy to evaluate",
     "We finish the part that was already working and never ship Luganda",
     "Phase 3 is explicitly the point of the plan; treat it as the success "
     "criterion rather than as an extension."],
], [1.55 * inch, 2.15 * inch, 3.2 * inch]))
gap(8)

story.append(Paragraph("Open questions", H2))
bullets([
    "<b>Every Tongue.</b> This document treats it as a third consumer of the "
    "same shared service, because that is the shape the architecture suggests. "
    "Its actual requirements are unknown here &mdash; nothing about it exists "
    "in the codebase &mdash; so this is an assumption, flagged as one. If it "
    "has different needs, particularly around live or user-supplied text, "
    "§5's balance between the pre-rendered and on-demand tiers is the part "
    "that would change.",
    "<b>Do we publish the datasets and voices we create?</b> Recommended yes, "
    "with speaker consent: an openly-licensed Luganda voice would be a genuine "
    "contribution, and it costs us nothing we are keeping.",
    "<b>Where does the batch pipeline run?</b> It has no latency requirement, so "
    "it can be the cheapest compute we can find rather than anything "
    "co-located with the API.",
    "<b>Human narration for the highest-value works?</b> A well-read chapter "
    "beats any synthetic voice. It does not scale to 2,414 chapters, but it may "
    "be right for a handful, and the same delivery pipeline serves both.",
])

story.append(Paragraph("What we need to decide first", H2))
story.append(table([
    ["#", "Decision", "Blocks"],
    ["1", "Do we add the pre-render track alongside the committed in-browser "
     "plan, or wait for the spike result first?", "Phase 2&#8242; onward"],
    ["2", "What licence floor do we hold engines and models to?", "Phase 3 engine choice"],
    ["3", "Is Luganda the first low-resource target, or Swahili?",
     "Phase 3 recruitment"],
    ["4", "Who owns native-speaker review capacity for audio, given the same "
     "people are needed for translation review?", "Phase 3 and 4 timelines"],
], [0.3 * inch, 4.6 * inch, 2.0 * inch]))

gap(10)
story.append(_rule())
gap(6)
para(
    "The short version: we already have the hard part &mdash; a clean, "
    "licensed, finite corpus in eight languages, and a reader that knows how "
    "to speak it. What is missing is a voice for the people who need it most, "
    "and a pipeline that makes giving them one a fixed cost rather than a "
    "recurring one.", S("close", parent=BODY, fontName="Times-Italic",
                        fontSize=9.8, leading=13.6, textColor=MUTED))


# ============================================================ frame / chrome
def chrome(canvas, doc):
    canvas.saveState()
    n = canvas.getPageNumber()
    if n > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(0.8 * inch, 10.32 * inch, 7.7 * inch, 10.32 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.8 * inch, 10.44 * inch,
                          "Free text-to-speech for Ochorus, Take Root and Every Tongue")
        canvas.drawRightString(7.7 * inch, 10.44 * inch, "Page %d of 10" % n)
    canvas.restoreState()


doc = BaseDocTemplate(OUT, pagesize=LETTER,
                      leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                      topMargin=0.75 * inch, bottomMargin=0.7 * inch,
                      title="Building the best free text-to-speech system",
                      author="Ochorus")
frame = Frame(0.8 * inch, 0.7 * inch, 6.9 * inch, 9.55 * inch, id="f",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=chrome)])
doc.build(story)
print("built", OUT)
