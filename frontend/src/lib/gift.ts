/**
 * "Give this book": a link that carries a book and a short note from the
 * person giving it, and the landing page that opens it (routes/gift).
 *
 * No backend. The whole gift — book slug, edition language, the giver's first
 * name and their note — rides in the URL's FRAGMENT (`/gift#g=<payload>`):
 *
 *   * a fragment is never sent to a server, so a note never lands in Render's
 *     access logs or the API; Sentry drops the hash ($lib/sentryScrub); and the
 *     landing page takes it off the address bar as soon as it is read, before
 *     Plausible's script (which reports `location.href`, fragment and all)
 *     sends anything. The gift's share menu is WhatsApp + email only — never
 *     Facebook's sharer, which would carry the link in a query string;
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
/** Longer than any honest payload — the caps above, even in emoji ZWJ
 *  sequences (~25 UTF-8 bytes a character), in base64url. Refused unread;
 *  `encodeGift` refuses to make one. */
const PAYLOAD_MAX = 16384;
const VERSION = 1;

export type Gift = { slug: string; lang: string; name: string; note: string };

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const LANG = /^[a-z]{2,3}$/;

/**
 * Links, written any of the ways a note might carry one: with a scheme
 * (`https://…`, `ftp://…`), `www.…`, an email address, a host with a path on
 * any TLD (`bit.ly/x`, `scam.ai/login`), or a bare host on a TLD from the
 * list (`example.com`). A bare `word.word` is not enough — a missing space
 * after a full stop is not a link ("Obrigado.Eu orei", "Love you.Live for
 * Him") — so the list leaves out every TLD that is also a word in a locale we
 * serve; those count only with a path. Matching runs on a copy with
 * fullwidth letters and look-alike dots (`bit．ly`, `example。com`) folded to
 * ASCII (`foldForLinks`). The note is a personal message on ochorus.com's
 * page: it must not become a way to send someone elsewhere. (It is shown as
 * plain text, never linked, so this is the second line, not the first.)
 */
const TLDS =
	'com|org|net|io|ly|co|biz|xyz|ru|cn|uk|br|ng|ke|ug|tz|za|ua|jp|kr|vn|ae|sa|eg|nz|nl|pl|asia|tk|ml|ga|cf|gg|tv|ws|gd|gl';
const LINK = new RegExp(
	[
		String.raw`\b[a-z][a-z0-9+.-]*:\/\/\S*`,
		String.raw`\bwww\.\S*`,
		String.raw`[^\s@]+@[^\s@]+\.[^\s@]+`,
		String.raw`\b(?:[a-z0-9-]+\.)+(?:${TLDS})\b(?:[/?#]\S*)?`,
		String.raw`\b(?:[a-z0-9-]+\.)+[a-z]{2,}\/\S*`
	].join('|'),
	'gi'
);

/** `s` with fullwidth ASCII and the dots that read as "." (ideographic,
 *  fullwidth, halfwidth, one-dot leader, small full stop) mapped to ASCII.
 *  Every mapping is one UTF-16 unit to one, so match offsets line up with
 *  `s` and only the link itself is cut — a Japanese "。" stays. */
const foldForLinks = (s: string): string =>
	s
		.replace(/[\uff01-\uff5e]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0))
		.replace(/[\u3002\uff61\u2024\ufe52]/g, '.');

/** Control and format characters — bidi overrides, embeddings, isolates and
 *  marks (incl. U+061C), zero-width spaces, tag characters (the invisible
 *  "ASCII smuggling" alphabet), soft hyphens — plus the blank-looking
 *  letters a name could be made of (Hangul fillers, braille blank) and the
 *  variation selectors outside the emoji block. Kept: tab and newline (tidied later), ZWJ
 *  (builds emoji), ZWNJ (load-bearing in Hindi and Persian), and the emoji
 *  variation selectors U+FE00–FE0F (❤️). RTL text needs none of the bidi
 *  controls — the page sets `dir="auto"` on it. */
const INVISIBLE =
	/(?![\t\n\u200c\u200d])[\p{Cc}\p{Cf}\u115f\u1160\u3164\uffa0\u2800\u180e]|\u034f|(?![\ufe00-\ufe0f])\p{Variation_Selector}/gu;

/** More than this many combining marks in a row is "Zalgo" (marks stacked
 *  until they paint over the page around the note); no script we serve stacks
 *  more than three on one letter. */
const MARK_RUN = /(\p{M}{4})\p{M}+/gu;

// Built once: the sheet counts and caps on every keystroke.
const segmenter =
	typeof Intl !== 'undefined' && 'Segmenter' in Intl
		? new Intl.Segmenter(undefined, { granularity: 'grapheme' })
		: null;

/** Split into user-perceived characters, so a cap never cuts an emoji or an
 *  accented letter in half. */
const graphemes = (s: string): string[] =>
	segmenter ? Array.from(segmenter.segment(s), (x) => x.segment) : (s.match(GRAPHEME_ISH) ?? []);

/** Where there is no Intl.Segmenter (Firefox < 125, old WebViews): a letter
 *  with its marks, skin tone and ZWJ-joined partners — close enough that the
 *  receiver's re-cap doesn't cut a note a Segmenter-equipped sender wrote. */
const GRAPHEME_ISH = /\P{M}[\p{M}\u{1f3fb}-\u{1f3ff}]*(?:\u200d\P{M}[\p{M}\u{1f3fb}-\u{1f3ff}]*)*|\p{M}+/gsu;

/** How many characters `s` counts as against a cap. */
export const giftLength = (s: string): number => graphemes(s).length;

/** `s` cut to at most `max` characters (graphemes); the sheet's inputs use it
 *  as the reader types, the cleaners after tidying. */
export const giftCap = (s: string, max: number): string => {
	const g = graphemes(s);
	return g.length > max ? g.slice(0, max).join('').trimEnd() : s;
};

export type Cleaned = { text: string; removedLinks: boolean };

/** Strip links, invisible/control characters and mark pile-ups. `max`
 *  pre-cuts the raw text (to twice the cap, room for what tidying removes)
 *  so a hand-made payload never makes the link scan work on kilobytes. */
function scrub(raw: string, max: number): Cleaned {
	const text = giftCap(String(raw ?? ''), max * 2)
		.normalize('NFC')
		.replace(/\r\n?|[\u2028\u2029]/g, '\n')
		.replace(INVISIBLE, '')
		.replace(MARK_RUN, '$1');
	const links = [...foldForLinks(text).matchAll(LINK)];
	let out = text;
	for (const m of links.reverse()) out = out.slice(0, m.index) + out.slice(m.index + m[0].length);
	return { text: out, removedLinks: links.length > 0 };
}

/** A name needs something to see: a letter, digit or symbol (emoji). */
const VISIBLE = /[\p{L}\p{N}\p{S}]/u;

/** The giver's first name: one line, links and invisibles gone, capped. */
export function cleanGiftName(raw: string): Cleaned {
	const { text, removedLinks } = scrub(raw, GIFT_NAME_MAX);
	const name = giftCap(text.replace(/\s+/g, ' ').trim(), GIFT_NAME_MAX);
	return { text: VISIBLE.test(name) ? name : '', removedLinks };
}

/** The note: plain text, at most one blank line between paragraphs, capped. */
export function cleanGiftNote(raw: string): Cleaned {
	const { text, removedLinks } = scrub(raw, GIFT_NOTE_MAX);
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
	const payload = toBase64Url(JSON.stringify([VERSION, gift.slug, gift.lang, name, note]));
	// decodeGift would refuse it unread: say so here, not on the recipient's screen.
	if (payload.length > PAYLOAD_MAX) throw new Error('gift too long');
	return payload;
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
