/**
 * The shared ground every Ochorus Open Graph card is drawn on.
 *
 * Two scripts render 1200×630 share images — `generate-og.mjs` (the fixed
 * browse-page cards) and `generate-sermon-og.mjs` (one per sermon) — and a
 * share card that doesn't look like the others is worse than no share card at
 * all: the whole point is that a link forwarded into a WhatsApp group is
 * recognisably Ochorus. So the ground, the palette and the faces live here
 * once rather than being retyped per script and drifting apart.
 *
 * NOT part of the build or CI. Both callers are hand-run when the card set or
 * the branding changes, and their output is committed:
 *
 *     cd frontend
 *     npm i -D satori @resvg/resvg-js        # build-only, not app deps
 *     node scripts/generate-og.mjs
 *     node scripts/generate-sermon-og.mjs
 *
 * satori needs a real TTF/OTF (it can't read the app's woff2 variable fonts),
 * so this uses the Liberation faces shipped with most Linux distros — a clean
 * classic serif that suits a public-domain-classics library. Swap FONT_* below
 * for the brand faces (Fraunces / Hanken) if TTFs of them are vendored.
 */
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

/** The Open Graph canvas. 1.91:1, what Facebook/WhatsApp/X all crop to. */
export const WIDTH = 1200;
export const HEIGHT = 630;

// Brand tokens (dark theme) — warm black → deep indigo, gold wordmark.
export const BG_FROM = '#16130f';
export const BG_TO = '#241f3f';
export const GOLD = '#e0b45c';
export const PAPER = '#faf6ef';
export const MUTED = '#b7afd6';

export const BACKGROUND = `linear-gradient(135deg, ${BG_FROM} 0%, ${BG_TO} 100%)`;

const FONT_SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf';
const FONT_SANS = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf';

export const FONTS = [
	{ name: 'serif', data: readFileSync(FONT_SERIF), weight: 700, style: 'normal' },
	{ name: 'sans', data: readFileSync(FONT_SANS), weight: 400, style: 'normal' }
];

/** Lay out one satori node and write it as a PNG, creating the directory. */
export async function renderCard(node, outPath) {
	const svg = await satori(node, { width: WIDTH, height: HEIGHT, fonts: FONTS });
	const png = new Resvg(svg, { fitTo: { mode: 'width', value: WIDTH } }).render().asPng();
	mkdirSync(dirname(outPath), { recursive: true });
	writeFileSync(outPath, png);
}

// ── Ink safety ──────────────────────────────────────────────────────────────
// A card can carry a per-item accent (a sermon's emblem hue), and those hues
// were picked to sit on the app's *light* surfaces, not on this near-black
// ground. `liftToContrast` is the OG card's answer to covers.py's `ink_safe`:
// the accent yields to legibility rather than the other way round.

const channels = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

/** WCAG relative luminance of a #rrggbb colour. */
export function luminance(hex) {
	const [r, g, b] = channels(hex).map((c) => {
		const s = c / 255;
		return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two #rrggbb colours. */
export function contrast(a, b) {
	const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return (hi + 0.05) / (lo + 0.05);
}

/**
 * The lighter of the two gradient stops — where an accent has the LEAST
 * contrast to work with. Measured at the worst point rather than the average,
 * for the same reason covers.py measures the byline at the frame and not at
 * its centre: an accent floored against the mean still fails at one end.
 */
export const WORST_GROUND = luminance(BG_FROM) > luminance(BG_TO) ? BG_FROM : BG_TO;

/**
 * The bar an accent has to clear. Every line these cards set an accent in is
 * WCAG "large text" — the eyebrow at 26px and the scripture reference at 30px
 * are both past the 24px threshold for normal weight — so 1.4.3 asks 3:1 of
 * them, not 4.5:1. The distinction is the same one covers.py draws between a
 * book cover's 23px byline (4.5) and its 34-60px title (3), and it is not
 * pedantry: floored to 4.5 the darker emblem hues wash out to grey, which is
 * both uglier AND less useful, since a grey accent stops being distinguishable
 * from the muted byline underneath it.
 */
export const LARGE_TEXT_CONTRAST = 3;

/**
 * Brighten `hex` until it clears `target` against `against`.
 *
 * Scaled channel-wise (`coverArt.ts:shade` with a factor above 1) rather than
 * blended toward white: blending drags every hue to the same pale grey on the
 * way up, so the emblems drawn in deep slate and navy — the raven, the rock,
 * Paul at prayer — came out lettering their cards in something you could not
 * tell from the byline. Scaling holds the ratio between the channels, so a
 * lifted navy is still navy.
 */
export function liftToContrast(hex, against = WORST_GROUND, target = LARGE_TEXT_CONTRAST) {
	let rgb = channels(hex);
	// 120 steps of 4% takes even a near-black ink to clipped white, so the loop
	// always terminates on the ratio rather than on the step count.
	for (let i = 0; i < 120; i++) {
		const out = `#${rgb.map((c) => Math.round(c).toString(16).padStart(2, '0')).join('')}`;
		if (contrast(out, against) >= target) return out;
		// The +1 floor is what lets a channel that is exactly 0 ever rise; without
		// it a pure blue would brighten while its red stayed pinned and the hue
		// would drift as it climbed.
		rgb = rgb.map((c) => Math.min(255, c * 1.04 + 1));
	}
	return PAPER;
}
