/**
 * A sermon's monogram, from the passage it expounds: "Matthew 11:28" → MAT / 11.
 *
 * The passage is data every sermon already carries, in every language, so the
 * mark is always its own and never needs a drawing. The parse is
 * language-blind on purpose — refs arrive as "Mateo 16:17", "1 Petro 1:3-4",
 * "يوحنا 1:29", "भजन संहिता 23:6" — so the book is simply the text before the
 * first chapter number, cut to a few graphemes (never code units: a Devanagari
 * conjunct or an Arabic letter must not be split).
 */
export interface SermonMonogram {
	/** Short book name ("MAT", "1 COR", "يوح"), upper-cased where the script has case; '' when there is no passage. */
	book: string;
	/** Chapter number as written — or, with no passage, the title's first letter. */
	chapter: string;
}

const BOOK_GRAPHEMES = 3;

const segmenter =
	typeof Intl !== 'undefined' && 'Segmenter' in Intl
		? new Intl.Segmenter(undefined, { granularity: 'grapheme' })
		: null;

function graphemes(text: string): string[] {
	return segmenter ? Array.from(segmenter.segment(text), (s) => s.segment) : Array.from(text);
}

function parseRef(ref: string): SermonMonogram | null {
	// A ref can list several passages ("John 3:16; Romans 5:8") — the first leads.
	const first = ref.split(/[;,]/)[0].trim();
	const m = first.match(/^(?:([1-3])\s*)?(\P{Nd}+)(\p{Nd}+)?/u);
	if (!m) return null;
	const [, ordinal, name, chapter = ''] = m;
	// Skip an ordinal suffix standing alone: Amharic writes 1 John as "1ኛ ዮሐንስ".
	const words = name.trim().split(/\s+/).filter(Boolean).map(graphemes);
	const word = words.find((g) => g.length > 1) ?? words[0];
	if (!word) return null;
	const short = word.slice(0, BOOK_GRAPHEMES).join('').toUpperCase();
	return { book: ordinal ? `${ordinal} ${short}` : short, chapter };
}

/** The passage's monogram; a sermon with no parseable passage wears its title's first letter. */
export function sermonMonogram(ref: string | null | undefined, title: string): SermonMonogram {
	return parseRef(ref ?? '') ?? { book: '', chapter: graphemes(title.trim())[0] ?? '' };
}
