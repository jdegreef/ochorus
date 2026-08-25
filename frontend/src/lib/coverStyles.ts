/**
 * WHICH house style a book's cover is set in — and nothing about how it looks.
 *
 * WHY THIS EXISTS
 * Until now a cover varied in exactly one way: its colour. The frame, the
 * byline, the wrap, the face and the size were identical on every book, so a
 * grid of them read as coloured slabs — `covers.py` says as much in its own
 * comments, and the topic emblem was added to give the composition a second
 * variable. This is the third, and the loudest: the TYPE.
 *
 * A cover is drawn in the browser now (see `BookCover.svelte`), which is what
 * makes this possible at all. The generated plate used to be an SVG served
 * through `<img>`, and such a document cannot reach the page's webfonts — so it
 * could only name faces the device already had, which in practice meant Georgia
 * on every cover in the library. Type in HTML can be set in anything we ship.
 *
 * THE DRAWING IS NOT HERE. This module returns a recipe's NAME; the recipe
 * itself — face, weight, size, tracking, case, ornament — is the matching
 * `.style-*` block in `components/cover-type.css`, in the only language that
 * renders it. Two renderers draw a cover (the component, and the share-card
 * script that photographs one), so the numbers live in the one file both of
 * them read rather than being carried through here into an inline `style`
 * attribute. This module decides; that file draws.
 *
 * KEYED BY AUTHOR, DEFAULTED BY ERA
 * Every author is entitled to a style; almost none needs a bespoke one. So the
 * table below lists an author only where they differ from what their century
 * would suggest, and `eraOf` supplies the rest. A new author therefore arrives
 * already dressed — an Ochorus contributor with no birth year included —
 * rather than falling back to a house default that would make them look
 * unfinished.
 *
 * DELIBERATELY IMPORT-FREE AT RUNTIME, like `emblems.ts` and for the same
 * reason: `scripts/generate-cover-og.mjs` loads this module straight from Node
 * under its type stripping, to set a book's share card in the style its cover
 * is set in. Bare Node resolves neither the `$lib` alias nor an extensionless
 * `./eras`, while naming the extension instead fails `svelte-check`. So the era
 * arrives as an argument — `eraOf` is called by the caller, one line either
 * side — rather than being reached for in here. `nodeLoadable.test.ts` fails if
 * a runtime import creeps back in.
 */
import type { EraId } from './eras';

/**
 * The recipes. Each is a century's printing seen from a distance, not a
 * reproduction: the point is that Augustine and Spurgeon should not look like
 * the same publisher had them, and that a reader who has met one Andrew Murray
 * cover recognises the next.
 *
 * Each id is a class — `.style-<id>` in `components/cover-type.css`, which is
 * where each of these is actually described. `coverStyles.test.ts` fails if one
 * of these has no block, or a block has no id here.
 */
export const COVER_STYLE_IDS = [
	'inscriptional', // Roman capitals, for the world Augustine wrote in
	'devotional', // a humanist old-style — the manual for the closet
	'press', // the Fell types the Puritans were printed in
	'enlightenment', // Baskerville, the Wesleys' century
	'revival', // a Victorian display face
	'house' // Fraunces, what the rest of the site is set in
] as const;

export type CoverStyleId = (typeof COVER_STYLE_IDS)[number];

/**
 * What a century wears when its author has no entry of their own.
 *
 * The buckets are `eras.ts`', unchanged and not re-cut here: era is the one
 * grouping a writer already belongs to on this site (it colours their card in
 * every list they appear in), and inventing a second, nearly-identical set of
 * date boundaries for covers is how two answers to "when is a Puritan" get
 * shipped.
 */
export const ERA_STYLE: Record<EraId, CoverStyleId> = {
	early: 'inscriptional',
	puritans: 'press',
	awakenings: 'enlightenment',
	missionary: 'revival',
	modern: 'house',
	contemporary: 'house'
};

/**
 * The authors whose books are not set in what their birth year suggests.
 *
 * Only the exceptions: an author who agrees with their era is absent, so this
 * table stays a list of JUDGEMENTS rather than a second copy of `ERA_STYLE`
 * that has to be kept in step with it. Each line says why.
 *
 * Two kinds of exception recur. A writer whose WORK belongs to the century
 * after their birth (`eraOf` reads a birth year, and a man born in 1686 who
 * publishes in 1729 is a Georgian author by every measure but that one); and a
 * writer whose REGISTER is not their century's — the missionary era is half the
 * library, and setting all fifteen of its authors in one Victorian display face
 * would reproduce, one era down, exactly the sameness this file exists to end.
 */
export const AUTHOR_STYLE: Record<string, CoverStyleId> = {
	// Born 1380, but a monk copying manuscripts for novices — the devotional
	// hand, not the Roman monument his era default would give him.
	'thomas-a-kempis': 'devotional',
	// French interior mysticism; nothing to do with the English press.
	'jeanne-guyon': 'devotional',
	// Born 1686, but `A Serious Call` is 1729 — a Georgian book.
	'william-law': 'enlightenment',
	// Born 1792, so `eraOf` files him with the Awakenings; `Lectures on Revivals
	// of Religion` is 1835, and he is the revival century's own subject.
	'charles-finney': 'revival',
	// The devotional writers of the missionary century. Murray, Meyer, Smith and
	// Carmichael wrote manuals for the closet, not addresses for the hall, and
	// they hold more of this library than anyone — Murray alone has seven
	// editions — so this is where one face for the whole era would be felt most.
	'andrew-murray': 'devotional',
	'frederick-brotherton-meyer': 'devotional',
	'hannah-whitall-smith': 'devotional',
	'amy-carmichael': 'devotional'
};

/**
 * The SCRIPTS a cover's metrics are corrected for — and nothing about the faces.
 *
 * WHICH FACE a script gets is not decided here and cannot be: font fallback is
 * per GLYPH, so `--cover-face-press` simply lists IM Fell, then Amiri, then
 * Tiro Devanagari, and the browser takes each character from the first family
 * that has it. Nothing has to know what language a title is in to pick a face.
 *
 * Nor does a script get six distinct faces. Arabic gets one with two weights
 * and Devanagari two; the six Latin recipes are six CENTURIES of Latin
 * printing, and there was no Fell type for Devanagari to revive. What carries
 * across is the loud-and-quiet of a title page, and that is what these blocks
 * preserve.
 *
 * What DOES need knowing is the METRICS. Every number in a `.style-*` recipe
 * was evened out by eye against a Latin face — `cover-type.css` says as much —
 * and three of those numbers are not merely untuned but WRONG in another
 * script:
 *
 * * `letter-spacing` breaks Arabic. It is cursive: its letters join, and
 *   tracking prises the joins apart into disconnected shapes. `inscriptional`
 *   asks for 0.06em, so Augustine in Arabic was the worst of the six.
 * * `font-style: italic` does not exist in Arabic or Devanagari. The browser
 *   obliges by SLANTING the upright — a synthesis nobody drew.
 * * A weight a face has not got is synthesised into the smeared-stem bold this
 *   module already refuses to ask a Latin face for. Amiri and Tiro ship fewer
 *   weights than the faces they stand beside.
 *
 * Latin is deliberately absent: it is what the recipes are already written in,
 * so a Latin cover needs no correction and carries no class.
 */
export const COVER_SCRIPTS = ['arabic', 'devanagari', 'cyrillic'] as const;

export type CoverScript = (typeof COVER_SCRIPTS)[number];

/**
 * Language code → the script its titles are set in; absent means Latin.
 *
 * BY LANGUAGE, NOT BY SNIFFING THE TITLE. A title is a handful of words and may
 * be entirely digits, a quoted Latin name or a scripture reference — so a cover
 * that chose its metrics from the characters a translator happened to type
 * would change design from one book to the next inside one shelf. The edition's
 * language is the fact; its title is a sample.
 *
 * Keyed to `Language.code` as the backend seeds it (`library/language_seed.py`).
 * A language this has never heard of is set exactly as it is today, which is
 * right for the next Latin-script language and no worse than today for anything
 * else — the same shape as `coverStyleFor` dressing an unknown author.
 */
const LANGUAGE_SCRIPT: Record<string, CoverScript> = {
	ar: 'arabic',
	hi: 'devanagari',
	uk: 'cyrillic'
};

/** The script a cover in this language is corrected for; null when Latin. */
export function scriptOf(language: string): CoverScript | null {
	return LANGUAGE_SCRIPT[language] ?? null;
}

/**
 * The style a book's cover is set in.
 *
 * Takes the era rather than deriving it (see the header on why this module
 * cannot import `eraOf`), so a caller writes
 * `coverStyleFor(eraOf(author.birth_year), author.slug)`.
 *
 * Total, and never null: an author the tables have never heard of — an admin
 * import, a contributor added this morning — comes back with their century's
 * recipe, and one with no birth year comes back in the house voice, because
 * `eraOf(null)` is `contemporary`.
 */
export function coverStyleFor(era: EraId, authorSlug: string): CoverStyleId {
	return AUTHOR_STYLE[authorSlug] ?? ERA_STYLE[era];
}
