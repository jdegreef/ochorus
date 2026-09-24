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
	'house', // Fraunces, what the rest of the site is set in
	'lettered', // hand-lettered small caps, for a living author whose own covers use them
	'originals', // Ochorus' own imprint, in the house face
	'young' // the site's sans, for books written or retold for children
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
	// Bounds joins them: born 1835 his era default is `revival`, a display face
	// for the hall, but his whole shelf is prayer manuals for the closet.
	'andrew-murray': 'devotional',
	'frederick-brotherton-meyer': 'devotional',
	'hannah-whitall-smith': 'devotional',
	'amy-carmichael': 'devotional',
	'e-m-bounds': 'devotional',
	// Ochorus' own books. Their author has no birth year, so they fell to the
	// house voice with every other living writer — and a publisher's imprint
	// that looks like everyone else's books is not an imprint.
	'ochorus-originals': 'originals',
	// His English editions wear the covers his ministry designed, all set in
	// hand-lettered small caps; without this his translations were the only
	// editions of those books in a different voice.
	'gareth-evans': 'lettered'
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

/**
 * The scripts that letter-spacing DAMAGES rather than merely mistunes.
 *
 * Data rather than prose, so that a cursive script added to `COVER_SCRIPTS`
 * fails the tracking gate naming what to do, instead of inheriting a Latin
 * arrangement in silence.
 *
 * Cyrillic is absent and belongs absent: it is not cursive, and tracked
 * capitals are as right for it as for Latin.
 *
 * OTHER LISTS NAME THE SAME TWO SCRIPTS AND ARE NOT THIS ONE. They are
 * deliberately not consolidated, because they are four different properties
 * that merely coincide today: a face that must not LEAD a stack (`coverStyles
 * .test.ts`, where a Cyrillic face may lead and an Arabic one may not); a
 * script with NO ITALIC (Cyrillic has one, so the fake-slant correction skips
 * it); a script `--font-sans` does not cover YET (`fontStacks.test.ts`, which
 * changes the day that token gains them); and this one, a script that tracking
 * damages. Folding them together would make a change to any one of them
 * silently move the other three.
 */
export const CURSIVE_SCRIPTS: readonly CoverScript[] = ['arabic', 'devanagari'];

export type CoverScript = (typeof COVER_SCRIPTS)[number];

/**
 * ISO 15924 script subtag → the recipe corrections that script needs.
 *
 * KEYED ON THE SCRIPT, NOT THE LANGUAGE, and that is the whole point. A table
 * of language codes would have to name `ar`, then `fa`, then `ur`, then `ps` —
 * and an admin can add a language to the registry WITHOUT A DEPLOY ("Add a
 * language" in the admin; see `library/language_seed.py` on who owns which).
 * So the day someone adds Urdu, a language table would still be right about
 * every language it listed and silently wrong about the new one: the FACE would
 * work, because font fallback is per glyph and does not care what language a
 * title is in, while every correction stopped — Urdu's cursive joins prised
 * apart by `inscriptional`'s tracking, its subtitle slanted by a synthesis
 * nobody drew. Those are the three defects this module calls wrong rather than
 * untuned, reappearing at full strength on the next language nobody thought
 * about.
 *
 * A script table cannot go stale that way. It grows only when a script needs
 * CSS that does not exist yet, which is a change to `cover-type.css` anyway.
 *
 * Absent scripts are Latin's case, deliberately: Latn is what the recipes are
 * already written in and needs no entry, and a script with no entry — Hebrew,
 * Ge'ez, Han — is set exactly as it is today rather than corrected by numbers
 * measured against a font nobody chose for it. That is the same shape as
 * `coverStyleFor` dressing an author it has never heard of.
 */
const SCRIPT_SUBTAG: Record<string, CoverScript> = {
	Arab: 'arabic',
	Deva: 'devanagari',
	Cyrl: 'cyrillic'
};

/**
 * The script a cover in this language is corrected for; null when it needs none.
 *
 * `Intl.Locale.maximize()` is what turns a bare language code into a script —
 * `ar` and `ur` and `fa` all maximise to `Arab`, `hi` and `mr` to `Deva` — so
 * this module never has to hold a list of the world's languages. It is a
 * global, not an import, which is what keeps this file loadable from bare Node
 * (`nodeLoadable.test.ts`).
 *
 * Anything unparseable comes back null and is set as it is today. That includes
 * a code no browser has heard of, and — on a browser too old for `Intl.Locale`
 * — every code, which degrades to exactly the behaviour before this existed
 * rather than to a broken one.
 */
export function scriptOf(language: string): CoverScript | null {
	try {
		const script = new Intl.Locale(language).maximize().script;
		return (script && SCRIPT_SUBTAG[script]) || null;
	} catch {
		return null;
	}
}

/**
 * The style a book's cover is set in.
 *
 * Takes the era rather than deriving it (see the header on why this module
 * cannot import `eraOf`), so a caller writes
 * `coverStyleFor(eraOf(author.birth_year), author.slug, book.slug)`.
 *
 * The book slug is required rather than optional: were it optional, a
 * renderer that left it off would still compile, and would draw every young
 * reader's cover in their author's century.
 *
 * Total, and never null: an author the tables have never heard of — an admin
 * import, a contributor added this morning — comes back with their century's
 * recipe, and one with no birth year comes back in the house voice, because
 * `eraOf(null)` is `contemporary`.
 */
export function coverStyleFor(era: EraId, authorSlug: string, bookSlug: string): CoverStyleId {
	return BOOK_STYLE[bookSlug] ?? AUTHOR_STYLE[authorSlug] ?? ERA_STYLE[era];
}

/**
 * The books whose AUDIENCE decides their cover, not their author or century.
 *
 * Every other table here asks when a book was written. A book retold for a
 * child answers a different question: Bunyan in words of one syllable is not a
 * Puritan title page, and dressing it in the Fell types — which his era gives
 * it — is how a children's shelf came to look like a row of scholarly editions.
 *
 * Keyed by BOOK because audience is a property of the work, not the writer: the
 * same author can be on both shelves, and `ochorus-originals` is. Consulted
 * before the author table for the same reason — it is the narrower claim.
 *
 * The For Young Readers shelf, as `topic_seed.py` lists it. Not derived from
 * `BookSummary.topics` at runtime, and that is not an oversight: the API drops
 * a shelf that has no title in the edition's language, so an Arabic or French
 * Brave for God would carry no chip and lose its style. The og script cannot
 * read the topic seed either, so both renderers read this.
 * `coverStyles.test.ts` fails when the shelf and this table disagree.
 */
export const BOOK_STYLE: Record<string, CoverStyleId> = {
	'pilgrims-progress-words-of-one-syllable': 'young',
	'divine-songs-for-children': 'young',
	'brave-for-god': 'young',
	'brave-for-god-2': 'young',
	'brave-for-god-3': 'young',
	'brave-for-god-4': 'young',
	'hurlbuts-life-of-christ': 'young',
	'rooted-1': 'young',
	'rooted-2': 'young',
	'rooted-3': 'young',
	'rooted-4': 'young',
	'rooted-5': 'young',
	'rooted-6': 'young',
	'daughters-of-the-king-1': 'young',
	'daughters-of-the-king-2': 'young',
	'sons-of-the-king-1': 'young',
	'sons-of-the-king-2': 'young',
	'daughters-of-the-king-3': 'young',
	'sons-of-the-king-3': 'young',
	// A series, not an audience: the Key Teachings are Ochorus' own companions,
	// so all four wear the imprint's face rather than each writer's century
	// (see coverLayouts.BOOK_LAYOUT for the other half of the series look).
	'key-teachings-of-a-b-simpson': 'originals',
	'key-teachings-of-jonathan-edwards': 'originals',
	'key-teachings-of-richard-baxter': 'originals',
	'key-teachings-of-watchman-nee': 'originals'
};

/**
 * A book's volume numeral in its edition's own digits, or null outside a series.
 *
 * The title often says it already ("Book Two"), and at a size a reader can read
 * a title that is enough. It is not enough on a shelf: a cover is mostly seen at
 * 48-64px, where the title is unreadable and three volumes of one series look
 * like three unrelated books. A numeral in a ring is the one thing that survives
 * there, which is also why it sits outside the container gate.
 *
 * `position` is the book's `series_position` — a field of the Book row, so the
 * component reads it off the API and the share-card script off the fixture, and
 * neither keeps a table. Null for a book in no series, and for a volume of an
 * unordered one (Key Teachings), which has no reading order to number.
 *
 * `Intl.NumberFormat` rather than the ASCII digit, so each language gets its
 * locale's DEFAULT numbering system from CLDR — Persian ۲, Marathi २ — without a
 * table of ours, the same reasoning that keeps `scriptOf` free of one. Arabic
 * and Hindi default to Western digits in current data, and that is CLDR's call
 * to make, not this module's. A global, not an import, like `Intl.Locale`.
 */
export function volumeNumeral(
	position: number | null | undefined,
	language: string
): string | null {
	if (!position) return null;
	try {
		return new Intl.NumberFormat(language).format(position);
	} catch {
		return String(position);
	}
}
