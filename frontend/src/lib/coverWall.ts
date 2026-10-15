/**
 * The cover wall's judgements, apart from its drawing (`routes/admin/covers`).
 *
 * The cover gates hold each cover up on its own — contrast, digests,
 * provenance. What none of them can see is the SHELF: a painter given five
 * covers, a run of framed paintings so pale the scrim has all but hidden them,
 * a book still on a plate. These are those checks, kept pure so they are
 * tested rather than eyeballed.
 */
import type { AdminCover } from './library-admin';
import { coverLayoutFor } from './coverLayouts';
import { scrimStrength } from './coverScrim';

/** More works than this by one painter and the shelf starts to repeat itself
 *  (the 2026-10 cover review: George Inness on seven books read as one long
 *  brown landscape). A soft cap the wall flags, not a gate. */
export const PAINTER_CAP = 3;

/** A framed cover whose measured scrim is at least this strong shows its
 *  picture through a near-black veil — legible type bought with the art. */
export const HEAVY_SCRIM = 0.85;

export type CoverFlag = 'plate' | 'painter' | 'scrim';

export const FLAG_LABEL: Record<CoverFlag, string> = {
	plate: 'Still a plate',
	painter: `Painter on more than ${PAINTER_CAP} works`,
	scrim: `Scrim ≥ ${HEAVY_SCRIM}×`
};

/** Distinct WORKS per painter. A painting serves every language of its work,
 *  so counting editions would rank a translated book five times over. */
export function painterWorks(covers: AdminCover[]): Map<string, Set<string>> {
	const by = new Map<string, Set<string>>();
	for (const c of covers) {
		if (!c.artwork) continue;
		const works = by.get(c.artwork.artist) ?? new Set<string>();
		works.add(c.slug);
		by.set(c.artwork.artist, works);
	}
	return by;
}

/** Does this edition wear the framed composition — the one with a scrim? */
function isFramed(c: AdminCover): boolean {
	return coverLayoutFor(c.author.slug, null, c.slug, c.title) === null;
}

/** What is worth a second look about one edition, in the order the wall shows. */
export function coverFlags(c: AdminCover, painters: Map<string, Set<string>>): CoverFlag[] {
	const flags: CoverFlag[] = [];
	if (c.tier === 'plate' || c.tier === 'none') flags.push('plate');
	if (c.artwork && (painters.get(c.artwork.artist)?.size ?? 0) > PAINTER_CAP) flags.push('painter');
	const grounded = c.tier === 'painting' || c.tier === 'original' || c.tier === 'derived';
	if (grounded && isFramed(c) && scrimStrength(c.slug) >= HEAVY_SCRIM) flags.push('scrim');
	return flags;
}

export type WallGroup = 'none' | 'author' | 'painter' | 'tier' | 'colour';

/** One run of the wall under a heading (or none, for an ungrouped wall). */
export interface WallSection {
	key: string;
	label: string;
	covers: AdminCover[];
}

const TIER_ORDER = ['plate', 'none', 'other', 'painting', 'original', 'derived', 'designed'];

/**
 * Lay the wall out. `colour` is not a heading but an ORDER: every cover in one
 * run, sorted by its mean hue (`hues`, measured in the browser from the loaded
 * thumbnails), so a shelf that is all one colour shows up as one long band.
 * Covers not yet measured sort to the end.
 */
export function groupCovers(
	covers: AdminCover[],
	by: WallGroup,
	hues: Map<string, number> = new Map()
): WallSection[] {
	if (by === 'none') return [{ key: 'all', label: '', covers }];
	if (by === 'colour') {
		const hue = (c: AdminCover) => hues.get(editionKey(c)) ?? 999;
		return [{ key: 'colour', label: '', covers: [...covers].sort((a, b) => hue(a) - hue(b)) }];
	}
	const keyOf = (c: AdminCover): [string, string] =>
		by === 'author'
			? [c.author.slug, c.author.name]
			: by === 'painter'
				? c.artwork
					? [c.artwork.artist, c.artwork.artist]
					: ['~', 'Not a museum painting']
				: [c.tier, c.tier];
	const runs = new Map<string, WallSection>();
	for (const c of covers) {
		const [key, label] = keyOf(c);
		const run = runs.get(key) ?? { key, label, covers: [] };
		run.covers.push(c);
		runs.set(key, run);
	}
	const sections = [...runs.values()];
	if (by === 'tier') return sections.sort((a, b) => TIER_ORDER.indexOf(a.key) - TIER_ORDER.indexOf(b.key));
	if (by === 'painter') {
		// Most-used painter first: the repeats the cap is about lead the wall.
		const works = (s: WallSection) => (s.key === '~' ? -1 : new Set(s.covers.map((c) => c.slug)).size);
		return sections.sort((a, b) => works(b) - works(a) || a.label.localeCompare(b.label));
	}
	return sections.sort((a, b) => a.label.localeCompare(b.label));
}

/** One edition's identity on the wall. */
export const editionKey = (c: { slug: string; language: string }) => `${c.slug}|${c.language}`;

/** Hue in degrees (0–360) of an sRGB colour, or 999 for a grey (no hue to
 *  sort by — greys gather at the end rather than scattering among the reds). */
export function hueOf(r: number, g: number, b: number): number {
	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const d = max - min;
	if (d < 12) return 999;
	let h: number;
	if (max === r) h = ((g - b) / d) % 6;
	else if (max === g) h = (b - r) / d + 2;
	else h = (r - g) / d + 4;
	return (h * 60 + 360) % 360;
}
