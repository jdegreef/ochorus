import type { Season } from './liturgical';
import { artSlug } from './groundBars';

/**
 * The home hero's painting when the reader has none of their own (no book in
 * progress, or one without a painted ground): one per season of the Church
 * year, each already on the site as a book's wordless ground, so nothing new
 * is fetched or stored. Landscapes and skies, not scenes — the cover art
 * direction (curated_art.py) holds here too: a mood of the season, never a
 * face. Founder-approved set, 2026-10-07.
 */
export const SEASON_ART: Record<Season, string> = {
	advent: '/covers/art/john-hyde-a-life-640.webp', // Inness, Moonrise: waiting in the dark
	christmas: '/covers/art/mortification-of-sin-640.webp', // Griffier, Winter Landscape
	epiphany: '/covers/art/mortification-of-sin-640.webp',
	lent: '/covers/art/life-of-antony-640.webp', // Huguet, Ravine Near Biskra: the desert
	holyWeek: '/covers/art/days-of-heaven-upon-earth-640.webp', // Church, Twilight in the Wilderness
	easter: '/covers/art/religious-affections-640.webp', // Claude, Sunrise
	pentecost: '/covers/art/power-from-on-high-new-testament-640.webp', // Vedder, Storm in Umbria: the wind
	ordinary: '/covers/art/absolute-surrender-640.webp' // Van Gogh, Cypresses
};

export interface ArtCredit {
	artist: string;
	title: string;
	year: string;
	/** The book page's full credit line, collection and licence included. */
	credit: string;
}

// The book slug a `/covers/art/` painting was cut for (see groundBars).
export { artSlug };

let credits: Promise<Record<string, ArtCredit>> | null = null;

/**
 * The museum's own label for a painting: artist, title, year, exactly as
 * `curated_art.py` records them. Read from `/covers/art/credits.json`
 * (`backend/scripts/export_art_credits.py`), fetched once per page load and
 * only by the hero that shows it. Null for a painting with no curated entry
 * (a derived ground) or when the file can't be had — the hero then simply
 * hangs the picture unlabelled.
 */
export async function artCredit(url: string): Promise<ArtCredit | null> {
	const slug = artSlug(url);
	if (!slug) return null;
	credits ??= fetch('/covers/art/credits.json')
		.then((r) => (r.ok ? r.json() : {}))
		.catch(() => ({}));
	return (await credits)[slug] ?? null;
}
