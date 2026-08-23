/**
 * The house style a book's cover is set in — one recipe per author.
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
 * WHAT VARIES, AND WHAT DOES NOT
 * The TITLE carries the style: its face, weight, case, tracking, size and the
 * rule beneath it. The byline and the subtitle stay in the house serif on every
 * cover, and so do the frame, the mark, the scrim and the geometry.
 *
 * That split is deliberate twice over. It is how a real imprint gets variety
 * without fragmenting — the grid holds the shelf together while the title says
 * which book this is — and it halves what a reader downloads: the title is one
 * upright face per cover, where letting the subtitle follow would pull an
 * italic of each as well.
 *
 * KEYED BY AUTHOR, DEFAULTED BY ERA
 * Every author is entitled to a style; almost none needs a bespoke one. So the
 * table below lists an author only where they differ from what their century
 * would suggest, and `eraOf` supplies the rest. A new author therefore arrives
 * already dressed — an Ochorus contributor with no birth year included — rather
 * than falling back to a house default that would make them look unfinished.
 *
 * DELIBERATELY IMPORT-FREE AT RUNTIME, like `emblems.ts` and for the same
 * reason: `scripts/generate-cover-og.mjs` loads this module straight from Node
 * under its type stripping, to set a book's SHARE CARD in the face its cover is
 * set in. Bare Node resolves neither the `$lib` alias nor an extensionless
 * `./eras`, while naming the extension instead fails `svelte-check`. So the era
 * arrives as an argument — `eraOf` is called by the caller, one line either side
 * — rather than being reached for in here. `nodeLoadable.test.ts` fails if a
 * runtime import creeps back in.
 *
 * NON-LATIN SCRIPTS DEGRADE, BY DESIGN
 * Every stack below ends in `var(--font-display)`, and none of these faces
 * covers Arabic or Devanagari, so an Arabic title falls through to the same
 * stack it uses today — per glyph, which is exactly what font fallback is for.
 * Those covers keep their identity from the artwork and the colour instead.
 */
import type { EraId } from './eras';

/** The rule under the title. Three treatments, so the ornament varies too. */
export type CoverRule = 'plain' | 'double' | 'diamond';

export interface CoverStyle {
	/** The recipe's name — also the class the rule ornament is drawn from. */
	id: CoverStyleId;
	/**
	 * The token naming the title's face — never a family. The stacks live in
	 * `app.css` beside the @import that loads them, and every one of them ends
	 * at `--font-display` (see header).
	 */
	face: string;
	/**
	 * The title's weight, as a NUMBER the face actually has.
	 *
	 * Two of the five faces are static 400-only files. Asking 600 of those makes
	 * the browser synthesise a bold — smeared stems, filled counters — which at
	 * cover sizes is the most visible way to make a good face look cheap. So the
	 * weight belongs to the recipe rather than to the component.
	 */
	weight: number;
	/** `text-transform` for the title. */
	transform: 'none' | 'uppercase';
	/** Title tracking, in em. Caps need it; text faces mostly do not. */
	tracking: string;
	/**
	 * Multiplier on the title's base size.
	 *
	 * Faces of one nominal size are not of one APPARENT size: Cinzel is
	 * all-caps and so runs to cap height everywhere, EB Garamond has a small
	 * x-height and reads a step down, Libre Baskerville a large one and reads a
	 * step up. Set flat, the shelf's titles would visibly disagree about how big
	 * a title is. These are eyeballed at 128px — the size beside a book's
	 * details, and the largest a cover is seen at outside its own page.
	 */
	scale: number;
	rule: CoverRule;
}

export type CoverStyleId =
	| 'inscriptional'
	| 'devotional'
	| 'press'
	| 'enlightenment'
	| 'revival'
	| 'house';

/**
 * The recipes.
 *
 * Each is a century's printing seen from a distance, not a reproduction: the
 * point is that Augustine and Spurgeon should not look like the same publisher
 * had them, and that a reader who has met one Andrew Murray cover recognises
 * the next.
 */
export const COVER_STYLES: Record<CoverStyleId, CoverStyle> = {
	// Roman inscriptional capitals — the lettering of the world Augustine wrote
	// in. Caps only, so it is tracked and set a step down: at 1.0 the cap height
	// alone overran the plate that mixed-case titles fit inside.
	inscriptional: {
		id: 'inscriptional',
		face: 'var(--cover-face-inscriptional)',
		weight: 600,
		transform: 'uppercase',
		tracking: '0.06em',
		scale: 0.8,
		rule: 'plain'
	},
	// A humanist old-style — the hand of the devotional manual, from à Kempis'
	// monastery to Murray's study. Quiet, and the largest of the five, because
	// Garamond's x-height is the smallest.
	devotional: {
		id: 'devotional',
		face: 'var(--cover-face-devotional)',
		weight: 500,
		transform: 'none',
		tracking: '0.005em',
		scale: 1.1,
		rule: 'diamond'
	},
	// The Fell types, cut in the 1670s and used by the Oxford press — the metal
	// Bunyan and Baxter were actually printed in. Deliberately irregular; that
	// is the face, not a rendering fault.
	press: {
		id: 'press',
		face: 'var(--cover-face-press)',
		weight: 400,
		transform: 'none',
		tracking: '0',
		scale: 1.0,
		rule: 'double'
	},
	// Baskerville, cut in the 1750s — the transitional face of the Wesleys'
	// century, and of the sermons printed in it.
	enlightenment: {
		id: 'enlightenment',
		face: 'var(--cover-face-enlightenment)',
		weight: 400,
		transform: 'none',
		tracking: '0.01em',
		scale: 0.88,
		rule: 'plain'
	},
	// A high-contrast Victorian display face for the revival and missionary
	// century — the register of a Spurgeon title page. Weight 600 rather than
	// 700: a didone's hairlines drop out first, and a cover is often 40px.
	revival: {
		id: 'revival',
		face: 'var(--cover-face-revival)',
		weight: 600,
		transform: 'none',
		tracking: '0',
		scale: 1.0,
		rule: 'plain'
	},
	// The house voice, for writers of our own century and for Ochorus' own
	// titles. Fraunces is what the rest of the site is set in, so a contemporary
	// book looks like the app that published it.
	house: {
		id: 'house',
		face: 'var(--cover-face-house)',
		weight: 600,
		transform: 'none',
		tracking: '0',
		scale: 1.0,
		rule: 'plain'
	}
};

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
export function coverStyleFor(era: EraId, authorSlug: string): CoverStyle {
	return COVER_STYLES[AUTHOR_STYLE[authorSlug] ?? ERA_STYLE[era]];
}
