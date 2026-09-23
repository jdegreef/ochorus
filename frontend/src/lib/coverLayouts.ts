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
 * `framed` is that original composition and stays the default: a book whose
 * author is not in the table below looks exactly as it did. Only a PAINTING takes a layout. A
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
 * The authors whose painted covers are composed in something other than
 * `framed`, by author slug. KEYED BY AUTHOR, like `coverStyles.AUTHOR_STYLE`:
 * a reader who has met one Andrew Murray cover should recognise the next, so
 * every painted book by an author wears one layout in one colour, and every
 * edition of it too.
 *
 * Deliberately not everyone. The framed composition is a look worth keeping,
 * and a shelf where every author has a layout of their own is as uniform as one
 * where none does. An author not listed here stays framed.
 *
 * `coverLayouts.test.ts` fails when an author here has no painted book in
 * English, and when a railed author has a title too long for the rail.
 */
export const AUTHOR_LAYOUT: Record<string, CoverLayout> = {
	'a-b-simpson': { layout: 'box', hue: 'teal' },
	'andrew-murray': { layout: 'wash', hue: 'sage' },
	'athanasius-of-alexandria': { layout: 'rail', hue: 'indigo' },
	'augustine-of-hippo': { layout: 'rail', hue: 'rust' },
	'charles-h-spurgeon': { layout: 'band', hue: 'oxblood' },
	'dwight-l-moody': { layout: 'duotone', hue: 'indigo' },
	'e-m-bounds': { layout: 'split', hue: 'navy' },
	'george-muller': { layout: 'split', hue: 'oxblood' },
	'hudson-taylor': { layout: 'rail', hue: 'teal' },
	'john-bunyan': { layout: 'band', hue: 'teal' },
	'john-wesley': { layout: 'split', hue: 'mauve' },
	'jonathan-edwards': { layout: 'fade', hue: 'slate' },
	'r-a-torrey': { layout: 'diagonal', hue: 'ochre' },
	'richard-baxter': { layout: 'box', hue: 'rust' },
	'thomas-watson': { layout: 'fade', hue: 'oxblood' }
};

/** The scripts a title cannot be turned sideways in. */
const SIDEWAYS_UNSAFE = new Set(['arabic', 'devanagari']);

/**
 * The layout a painted cover is drawn in, or null for `framed`.
 *
 * `script` is `coverStyles.scriptOf`'s answer for the edition. The rail sets
 * its title sideways, which suits a Latin or Cyrillic title and mangles an
 * Arabic or Devanagari one — a cursive or hanging script turned on its side —
 * so those editions of a railed author's books take the title box instead,
 * in the same colour.
 */
export function coverLayoutFor(authorSlug: string, script: string | null): CoverLayout | null {
	const found = AUTHOR_LAYOUT[authorSlug];
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
