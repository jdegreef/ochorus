/**
 * "Give this book": a link that carries a book and a short note from the
 * person giving it, and the landing page that opens it (routes/gift).
 *
 * No backend. The whole gift — book slug, edition language, the giver's first
 * name and their note — rides in the URL's FRAGMENT (`/gift#g=<payload>`):
 *
 *   * a fragment is never sent to a server, so a note never lands in Render's
 *     access logs, the API, or Plausible (which counts the path only); Sentry
 *     drops the hash too ($lib/sentryScrub);
 *   * the static host only ever sees `/gift`, one client-only shell route, so
 *     there is nothing per-gift to prerender, crawl or put in a sitemap;
 *   * the payload is UTF-8 JSON in base64url: ~1.33 bytes per byte, where
 *     percent-encoding costs 3 — a 280-character note in Amharic or Hindi
 *     (3 UTF-8 bytes a character) is ~1.1 KB of link instead of ~2.5 KB.
 *
 * Anyone can write such a link by hand, so everything decoded is untrusted:
 * `decodeGift` re-validates the slug and language and re-cleans the name and
 * note exactly as the sender's sheet did, and the page renders them as plain
 * text (never `{@html}`), checks the book really exists in that language, and
 * keeps the note out of <title> and every meta tag.
 */

/** The giver's first name, in graphemes. */
export const GIFT_NAME_MAX = 40;
/** The note, in graphemes — one text message's worth. */
export const GIFT_NOTE_MAX = 280;
/** Longer than any honest payload (the caps above, base64url) — refused unread. */
const PAYLOAD_MAX = 4096;
const VERSION = 1;

export type Gift = { slug: string; lang: string; name: string; note: string };

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const LANG = /^[a-z]{2,3}$/;

/**
 * Links, written any of the ways a note might carry one: with a scheme
 * (`https://…`, `ftp://…`), `www.…`, an email address, or a bare host on a
 * common TLD (`bit.ly/x`, `example.com`). A bare `word.word` is not enough —
 * "Mr.Smith" or a missing space after a full stop is not a link — so a bare
 * host needs a TLD from the list — and a TLD that is also a common word
 * ("me", "to", "it", "in": "Read it.It changed me") only counts with a path
 * after it (`wa.me/123`). The note is a personal message on ochorus.com's
 * page: it must not become a way to send someone elsewhere.
 */
const TLDS =
	'com|org|net|io|ly|co|info|biz|xyz|app|link|site|online|shop|store|top|click|live|club|dev|gg|tv|cc|ws|gl|gd|tk|ml|ga|cf|ru|cn|uk|fr|pt|br|ng|ke|ug|tz|za|ua|jp|kr|vn|ae|sa|eg|et|ca|au|nz|ch|nl|pl|eu|asia|church|bible';
const WORD_TLDS = 'me|to|it|in|be|us|de|es|at|is|am|so|no|my|do|id|la|im';
const LINK = new RegExp(
	[
		String.raw`\b[a-z][a-z0-9+.-]*:\/\/\S*`,
		String.raw`\bwww\.\S*`,
		String.raw`[^\s@]+@[^\s@]+\.[^\s@]+`,
		String.raw`\b(?:[a-z0-9-]+\.)+(?:${TLDS})\b(?:[/?#]\S*)?`,
		String.raw`\b(?:[a-z0-9-]+\.)+(?:${WORD_TLDS})\/\S*`
	].join('|'),
	'gi'
);

/** Bidi overrides/embeddings/isolates and the invisible characters a name
 *  could hide behind. Not the joiners: ZWJ builds emoji, ZWNJ is load-bearing
 *  in Hindi and Persian script. RTL text needs none of these — the page sets
 *  `dir="auto"` on it. */
// eslint-disable-next-line no-control-regex
const INVISIBLE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u200b\u200e\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\ufff9-\ufffb]/g;

/** Split into user-perceived characters, so a cap never cuts an emoji or an
 *  accented letter in half. */
function graphemes(s: string): string[] {
	if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
		const seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
		return Array.from(seg.segment(s), (x) => x.segment);
	}
	return Array.from(s);
}

/** How many characters `s` counts as against a cap. */
export const giftLength = (s: string): number => graphemes(s).length;

/** `s` cut to at most `max` characters (graphemes); the sheet's inputs use it
 *  as the reader types, the cleaners after tidying. */
export const giftCap = (s: string, max: number): string => {
	const g = graphemes(s);
	return g.length > max ? g.slice(0, max).join('').trimEnd() : s;
};

export type Cleaned = { text: string; removedLinks: boolean };

/** Strip links, invisible/control characters and stray whitespace. */
function scrub(raw: string): Cleaned {
	let text = String(raw ?? '')
		.normalize('NFC')
		.replace(/\r\n?|[\u2028\u2029]/g, '\n')
		.replace(INVISIBLE, '');
	const before = text;
	text = text.replace(LINK, '');
	return { text, removedLinks: text !== before };
}

/** The giver's first name: one line, links and invisibles gone, capped. */
export function cleanGiftName(raw: string): Cleaned {
	const { text, removedLinks } = scrub(raw);
	return { text: giftCap(text.replace(/\s+/g, ' ').trim(), GIFT_NAME_MAX), removedLinks };
}

/** The note: plain text, at most one blank line between paragraphs, capped. */
export function cleanGiftNote(raw: string): Cleaned {
	const { text, removedLinks } = scrub(raw);
	const tidy = text
		.split('\n')
		.map((line) => line.replace(/[^\S\n]+/g, ' ').trim())
		.join('\n')
		.replace(/\n{3,}/g, '\n\n')
		.trim();
	return { text: giftCap(tidy, GIFT_NOTE_MAX), removedLinks };
}

function toBase64Url(s: string): string {
	const bytes = new TextEncoder().encode(s);
	let bin = '';
	for (const b of bytes) bin += String.fromCharCode(b);
	return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromBase64Url(s: string): string {
	const b64 = s.replace(/-/g, '+').replace(/_/g, '/');
	const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4));
	const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
	return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

const validSlug = (s: unknown): s is string => typeof s === 'string' && s.length <= 120 && SLUG.test(s);
const validLang = (s: unknown): s is string => typeof s === 'string' && LANG.test(s);

/** The fragment's payload for a gift (cleaned again here, whatever the caller did). */
export function encodeGift(gift: Gift): string {
	if (!validSlug(gift.slug) || !validLang(gift.lang)) throw new Error('invalid gift book');
	const name = cleanGiftName(gift.name).text;
	const note = cleanGiftNote(gift.note).text;
	return toBase64Url(JSON.stringify([VERSION, gift.slug, gift.lang, name, note]));
}

/** The gift a payload carries, or null for anything that isn't one. */
export function decodeGift(payload: string | null | undefined): Gift | null {
	if (!payload || payload.length > PAYLOAD_MAX || !/^[A-Za-z0-9_-]+$/.test(payload)) return null;
	let data: unknown;
	try {
		data = JSON.parse(fromBase64Url(payload));
	} catch {
		return null;
	}
	if (!Array.isArray(data) || data[0] !== VERSION) return null;
	const [, slug, lang, name, note] = data;
	if (!validSlug(slug) || !validLang(lang)) return null;
	if (typeof name !== 'string' || typeof note !== 'string') return null;
	return { slug, lang, name: cleanGiftName(name).text, note: cleanGiftNote(note).text };
}

/** The `#g=…` fragment of a gift link. */
export const giftHash = (gift: Gift): string => `#g=${encodeGift(gift)}`;

/** The gift in a location hash (`#g=…`), or null. */
export function giftFromHash(hash: string): Gift | null {
	const m = /^#?g=([^&]*)/.exec(hash);
	return m ? decodeGift(m[1]) : null;
}

/** Plausible event names — props are a language label only, never a slug, a
 *  name or a note. */
export const GIFT_CREATED_EVENT = 'Gift created';
export const GIFT_OPENED_EVENT = 'Gift opened';
