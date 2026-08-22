/**
 * The shared ground every Ochorus OPEN GRAPH card is drawn on.
 *
 * (Not every shareable image: `src/lib/quoteCard.ts` renders quote cards on a
 * light paper ground, a deliberately different family, and lives in the app
 * where this build-time module cannot reach it.)
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
 *     cd frontend && npm run og:pages
 *     cd frontend && npm run og:sermons
 *
 * `satori` and `@resvg/resvg-js` are declared devDependencies, so a plain
 * `npm install` is all either needs.
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

// Named with its extension because this is a plain .mjs script: Node resolves
// it, and nothing type-checks this file. (`emblems.ts` itself cannot import
// coverArt the same way — see its header.)
import { channels, toHex } from '../src/lib/coverArt.ts';

/** The Open Graph canvas. 1.91:1, what Facebook/WhatsApp/X all crop to. */
export const WIDTH = 1200;
export const HEIGHT = 630;

// Brand tokens (dark theme) — warm black → deep indigo, gold wordmark.
const BG_FROM = '#16130f';
const BG_TO = '#241f3f';
export const GOLD = '#e0b45c';
export const PAPER = '#faf6ef';
export const MUTED = '#b7afd6';

export const BACKGROUND = `linear-gradient(135deg, ${BG_FROM} 0%, ${BG_TO} 100%)`;

const FONT_SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf';
const FONT_SANS = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf';

// Read on first render, not at import: 780 KB of TTF, and reading it eagerly
// makes the pure colour maths below unimportable (and untestable) on a machine
// without the Liberation faces installed.
let fonts;
const loadFonts = () =>
	(fonts ??= [
		{ name: 'serif', data: readFileSync(FONT_SERIF), weight: 700, style: 'normal' },
		{ name: 'sans', data: readFileSync(FONT_SANS), weight: 400, style: 'normal' }
	]);

/** Lay out one satori node and rasterize it. Returns the PNG bytes. */
export async function drawCard(node) {
	const svg = await satori(node, { width: WIDTH, height: HEIGHT, fonts: loadFonts() });
	return new Resvg(svg, { fitTo: { mode: 'width', value: WIDTH } }).render().asPng();
}

/** Draw one card and write it, creating the directory. */
export async function renderCard(node, outPath) {
	const png = await drawCard(node);
	mkdirSync(dirname(outPath), { recursive: true });
	writeFileSync(outPath, png);
}

// ── Ink safety ──────────────────────────────────────────────────────────────
// A card can carry a per-item accent (a sermon's emblem hue), and those hues
// were picked to sit on the app's *light* surfaces, not on this near-black
// ground. This is the OG card's answer to covers.py's `ink_safe`: the accent
// yields to legibility rather than the other way round.

/** WCAG relative luminance of a #rrggbb colour. */
function luminance(hex) {
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

// The lighter gradient stop — where an accent has the LEAST contrast to work
// with. Measured at the worst point, not the mean, for the same reason
// covers.py measures a byline at the frame rather than at its centre.
const WORST_GROUND = luminance(BG_FROM) > luminance(BG_TO) ? BG_FROM : BG_TO;

// 3:1, not 4.5:1: every line these cards set an accent in (26px eyebrow, 30px
// reference) is past WCAG's large-text threshold. Same distinction covers.py
// draws between a cover's 23px byline and its 34-60px title — and not pedantry,
// since floored to 4.5 the darker emblem hues wash out to a grey you cannot
// tell from the muted byline beneath them.
export const LARGE_TEXT_CONTRAST = 3;

/**
 * Brighten `hex` until it clears `target` against the card ground.
 *
 * Scaled channel-wise rather than blended toward white: blending drags every
 * hue to the same pale grey on the way up, which is how the emblems drawn in
 * deep slate and navy first came out lettering their cards in something you
 * could not tell from the byline. Scaling holds the ratio between the channels,
 * so a lifted navy is still navy.
 */
export function liftToContrast(hex, target = LARGE_TEXT_CONTRAST) {
	let rgb = channels(hex);
	// 120 steps of 4% take even a near-black ink to clipped white, so the loop
	// always exits on the ratio rather than on the step count. The +1 floor is
	// what lets a channel sitting at exactly 0 ever rise: without it a pure blue
	// would brighten while its red stayed pinned, and the hue would drift.
	for (let i = 0; i < 120; i++) {
		const out = toHex(rgb);
		if (contrast(out, WORST_GROUND) >= target) return out;
		rgb = rgb.map((c) => Math.min(255, c * 1.04 + 1));
	}
	return PAPER;
}
