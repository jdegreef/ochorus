/**
 * WHICH layout a painted cover is composed in, and in which colour — and
 * nothing about how either looks.
 *
 * WHY THIS EXISTS
 * Every painting used to be dressed the same way: full bleed, a measured black
 * scrim, white type inside a hairline frame. The scrim is what makes white
 * type legible over a picture nobody has chosen yet, and it is also why a shelf
 * of paintings reads as a shelf of dark rectangles. A layout changes what the
 * type sits ON: paper, a colour band, a panel — so the ink can be dark, the
 * painting can be shown at its own brightness, and neighbouring books stop
 * looking like one another.
 *
 * `framed` is that original composition and stays the default: a book not in
 * the table below looks exactly as it did. Only a PAINTING takes a layout. A
 * designed cover carries its words in its pixels, and a plate is a flat colour
 * with an emblem that the framed composition was drawn around.
 *
 * THE DRAWING IS NOT HERE, as with `coverStyles.ts`. Each layout is a
 * `.cover-layout-<id>` block and each hue a `.cover-hue-<id>` block in
 * `components/cover-type.css`, the one file both renderers read (the component,
 * and the share-card script). `coverLayouts.test.ts` fails when an id here has
 * no block there, and holds each hue's colours to contrast.
 *
 * DELIBERATELY IMPORT-FREE AT RUNTIME, for the reason `coverStyles.ts` gives:
 * `scripts/generate-cover-og.mjs` loads this under bare Node.
 */

/**
 * The compositions. Each id is a class, `.cover-layout-<id>`. The original — the
 * painting full bleed under a scrim — is not among them: it is the base
 * composition, which the manifest records as `framed`.
 */
export const COVER_LAYOUT_IDS = [
	'band', // a colour band, the title on paper, the painting below
	'box', // the painting at full brightness, the title on a paper panel
	'split', // the painting on the left, paper on the right
	'fade', // the title on paper, the painting rising out of the page below
	'diagonal', // a slanted paper panel over the painting
	'duotone', // the painting reprinted pale, in the book's colour
	'wash', // the painting full bleed, fading to paper behind the title
	'rail' // a paper rail up the left edge, the title running up it
] as const;

export type CoverLayoutId = (typeof COVER_LAYOUT_IDS)[number];

/**
 * The colours a layout is drawn in. Each id is a class, `.cover-hue-<id>`, declaring
 * a band colour, a paper and an ink. Nine, so that a shelf of six rarely
 * repeats one.
 */
export const COVER_HUE_IDS = [
	'oxblood',
	'mauve',
	'teal',
	'navy',
	'ochre',
	'sage',
	'indigo',
	'rust',
	'slate'
] as const;

export type CoverHueId = (typeof COVER_HUE_IDS)[number];

export interface CoverLayout {
	layout: CoverLayoutId;
	hue: CoverHueId;
}

/**
 * The works composed in something other than `framed`, by slug — so every
 * edition of a work wears the same layout, as every edition shares its
 * painting.
 *
 * Chosen for the shelf, not book by book in isolation: the point is variety
 * across a row, so a new entry is worth checking beside its neighbours on
 * /books. `coverLayouts.test.ts` fails when a slug here does not wear a
 * painting in English.
 */
export const BOOK_LAYOUT: Record<string, CoverLayout> = {
	'a-short-and-easy-method-of-prayer': { layout: 'band', hue: 'mauve' },
	'absolute-surrender': { layout: 'duotone', hue: 'indigo' },
	'all-of-grace': { layout: 'diagonal', hue: 'ochre' },
	'answers-to-prayer': { layout: 'split', hue: 'oxblood' },
	confessions: { layout: 'rail', hue: 'rust' },
	'on-loving-god': { layout: 'diagonal', hue: 'indigo' },
	'pilgrims-progress': { layout: 'box', hue: 'teal' },
	'power-through-prayer': { layout: 'duotone', hue: 'sage' },
	'religious-affections': { layout: 'fade', hue: 'navy' },
	'the-bruised-reed': { layout: 'box', hue: 'ochre' },
	'the-imitation-of-christ': { layout: 'wash', hue: 'slate' },
	'the-normal-christian-life': { layout: 'band', hue: 'rust' },
	'the-way-to-god': { layout: 'fade', hue: 'navy' },
	'till-he-come': { layout: 'split', hue: 'oxblood' },
	'true-vine': { layout: 'wash', hue: 'mauve' },
	'waiting-on-god': { layout: 'rail', hue: 'sage' }
};

/** The scripts a title cannot be turned sideways in. */
const SIDEWAYS_UNSAFE = new Set(['arabic', 'devanagari']);

/**
 * The layout a painted cover is drawn in, or null for `framed`.
 *
 * `script` is `coverStyles.scriptOf`'s answer for the edition. The rail sets
 * its title sideways, which suits a Latin or Cyrillic title and mangles an
 * Arabic or Devanagari one — a cursive or hanging script turned on its side —
 * so those editions of a railed work take the title box instead, in the same
 * colour.
 */
export function coverLayoutFor(slug: string, script: string | null): CoverLayout | null {
	const found = BOOK_LAYOUT[slug];
	if (!found) return null;
	if (found.layout === 'rail' && SIDEWAYS_UNSAFE.has(script ?? '')) {
		return { layout: 'box', hue: found.hue };
	}
	return found;
}

/** How the share-card manifest records a layout: `framed`, or `<layout>/<hue>`. */
export function layoutKey(layout: CoverLayout | null): string {
	return layout ? `${layout.layout}/${layout.hue}` : 'framed';
}
