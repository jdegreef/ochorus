/**
 * Verse set as verse.
 *
 * The importers set a poem quoted inside prose — Bunyan's rhymes, a hymn in a
 * sermon — as one `<p>` per line, and the sanitizer keeps no class, so a
 * four-line stanza reached the page as four paragraphs with a full paragraph
 * gap between each line. This finds those runs and marks them, so the reading
 * CSS (`.reading p.verse` in app.css) can set them as a stanza: tight leading,
 * an indent, the paragraph gap only after the last line.
 *
 * At render time, not in the stored body, on purpose: every `<p>` stays a `<p>`
 * of its own, so a paragraph index — the resume point, a highlight, a bookmark,
 * a translation aligned paragraph-for-paragraph with the English — still points
 * at the same text. Only a class is added, and only to a bare `<p>` (the
 * sanitizer strips every attribute, so a bare `<p>` is all a body has).
 *
 * The test is deliberately conservative — a missed stanza looks as it always
 * did, a prose paragraph set as verse looks broken. A run is verse when:
 * - it is at least three consecutive short paragraphs (≤ MAX_LINE characters,
 *   two words or more, nothing but whitespace between them), each opening on a
 *   capital — a broken prose fragment continues in lower case;
 * - at least two-thirds of its lines but the last end WITHOUT sentence-final
 *   punctuation (a run of short sentences is dialogue or a list, not verse);
 * - its lines average four words or more (a signature block — name, place,
 *   date — is short lines too).
 * A line that opens with a speaker's label ("Apollyon: Whence came you…") is
 * never verse, nor one ending in a numeral (a dateline). An opening quotation
 * mark starts a new run and a closing one ends it, so the prose that leads into
 * a quoted poem ("Then said Mercy,") is not swept into it.
 *
 * Where a source indented alternate lines (Gutenberg's hymns reach us as
 * `<p> If it be his blessed will,</p>`, the indent a leading space), those
 * lines are marked `indent` too — only when some lines of the stanza are and
 * some are not, so a source that pads every line indents none.
 */

/** The longest line, in characters, that may be a line of verse. */
export const MAX_LINE = 70;
const MIN_RUN = 3;

const PARA = /<p>([\s\S]*?)<\/p>/g;
const TAG = /<[^>]+>/g;
/** A Bible verse number as build_owb_book sets it (backend `text.VERSE_MARKER`). */
const VERSE_NUMBER = /<sup class="v"[^>]*>[^<]*<\/sup>/g;

/** Whether a chapter body carries Bible verse numbers. */
export const hasVerseNumbers = (html: string): boolean => html.includes('<sup class="v"');
const ENTITY: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
/** A trailing scripture citation, "(1 Corinthians 1:2)": not part of the line. */
const CITATION = /\s*\([^)]*\d[^)]*\)$/;
const OPENS_ON_CAPITAL = /^[\s"'“‘«]*\p{Lu}/u;
/** "Apollyon:" / "Christian." / "Mr. Worldly Wiseman:" — a speaker, not a line. */
const SPEAKER = /^\W*\p{Lu}[\p{L}.' ]{0,30}[.:]\s/u;
const SENTENCE_END = /[.?!][\s"'”’)\]»]*$/;
const OPEN_QUOTE = /^[“"]/;
const CLOSE_QUOTE = /[”"][\s.,;:!?—-]*$/;

function plain(inner: string): string {
	return inner
		// A Bible verse number (`<sup class="v">16</sup>`) is not part of the line.
		.replace(VERSE_NUMBER, '')
		.replace(TAG, '')
		.replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (m, e: string) =>
			e[0] === '#' ? String.fromCodePoint(Number('0' + e.slice(1))) : (ENTITY[e] ?? m)
		)
		.trim()
		.replace(CITATION, '');
}

const words = (line: string) => line.split(/\s+/).length;

function isLine(inner: string, text: string): boolean {
	return (
		!/<(?:br|p)\b/i.test(inner) &&
		text.length <= MAX_LINE &&
		words(text) >= 2 &&
		OPENS_ON_CAPITAL.test(text) &&
		!SPEAKER.test(text) &&
		!/\d$/.test(text)
	);
}

function isStanza(lines: string[]): boolean {
	if (lines.length < MIN_RUN) return false;
	const inner = lines.slice(0, -1);
	const open = inner.filter((l) => !SENTENCE_END.test(l)).length;
	const meanWords = lines.reduce((n, l) => n + words(l), 0) / lines.length;
	return open * 3 >= inner.length * 2 && meanWords >= 4;
}

interface Para {
	/** Offset of its `<p>` in the body. */
	start: number;
	text: string;
	/** Could be a line of verse (see isLine). */
	line: boolean;
	/** Only whitespace separates it from the paragraph before. */
	adjacent: boolean;
	/** The source indented it (a leading space inside the `<p>`). */
	indented: boolean;
}

/** The runs of `paras` that are verse, as [first, last] indexes. */
function verseRuns(paras: readonly Para[]): [number, number][] {
	const runs: [number, number][] = [];
	let first = -1;
	const close = (last: number) => {
		if (first >= 0 && isStanza(paras.slice(first, last + 1).map((p) => p.text))) runs.push([first, last]);
		first = -1;
	};
	paras.forEach((p, i) => {
		if (first >= 0 && (!p.line || !p.adjacent || OPEN_QUOTE.test(p.text))) close(i - 1);
		if (!p.line) return;
		if (first < 0) first = i;
		if (CLOSE_QUOTE.test(p.text)) close(i);
	});
	close(paras.length - 1);
	return runs;
}

/** `html` with each line of verse marked `class="verse"` (plus `indent` for a
 *  source-indented line), the last line of a stanza `verse stanza-end`.
 *  Everything else is returned untouched. Idempotent: a marked `<p>` is no
 *  longer a bare one. */
export function markVerse(html: string): string {
	if (!html) return html;
	const paras: Para[] = [];
	let prevEnd = -1;
	for (const m of html.matchAll(PARA)) {
		const text = plain(m[1]);
		paras.push({
			start: m.index,
			text,
			line: isLine(m[1], text),
			adjacent: prevEnd >= 0 && html.slice(prevEnd, m.index).trim() === '',
			indented: /^\s/.test(m[1])
		});
		prevEnd = m.index + m[0].length;
	}
	let out = '';
	let at = 0;
	for (const [a, b] of verseRuns(paras)) {
		const run = paras.slice(a, b + 1);
		const alternates = run.some((p) => p.indented) && !run.every((p) => p.indented);
		run.forEach((p, i) => {
			const cls = ['verse', alternates && p.indented && 'indent', i === run.length - 1 && 'stanza-end'];
			out += html.slice(at, p.start) + `<p class="${cls.filter(Boolean).join(' ')}">`;
			at = p.start + '<p>'.length;
		});
	}
	return at ? out + html.slice(at) : html;
}
