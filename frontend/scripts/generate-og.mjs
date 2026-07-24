/**
 * Generate branded Open Graph share images (1200×630 PNG) for the browse/list
 * pages and the topic/plan detail pages, which otherwise ship no og:image.
 *
 * Output: frontend/static/og/<name>.png — committed to the repo and served as
 * static assets (like the pre-rasterized book covers). This script is NOT part
 * of the build or CI; run it by hand when the card set or branding changes:
 *
 *     cd frontend
 *     npm i -D satori @resvg/resvg-js        # build-only, not app deps
 *     node scripts/generate-og.mjs
 *
 * satori needs a real TTF/OTF (it can't read the app's woff2 variable fonts),
 * so this uses the Liberation faces shipped with most Linux distros — a clean
 * classic serif that suits a public-domain-classics library. Swap FONT_* below
 * for the brand faces (Fraunces / Hanken) if TTFs of them are vendored.
 *
 * og:image text is English only (social scrapers rarely read localized cards);
 * the same image serves every locale of a page.
 */
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og');

const FONT_SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf';
const FONT_SANS = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf';

// Brand tokens (dark theme) — warm black → deep indigo, gold wordmark.
const BG_FROM = '#16130f';
const BG_TO = '#241f3f';
const GOLD = '#e0b45c';
const PAPER = '#faf6ef';
const MUTED = '#b7afd6';

const serif = readFileSync(FONT_SERIF);
const sans = readFileSync(FONT_SANS);

/** One card: gold OCHORUS wordmark, big serif title, muted subtitle. */
function card(title, subtitle) {
	return {
		type: 'div',
		props: {
			style: {
				width: '1200px',
				height: '630px',
				display: 'flex',
				flexDirection: 'column',
				justifyContent: 'space-between',
				padding: '80px',
				background: `linear-gradient(135deg, ${BG_FROM} 0%, ${BG_TO} 100%)`,
				fontFamily: 'sans'
			},
			children: [
				{
					type: 'div',
					props: {
						style: {
							fontSize: 34,
							letterSpacing: 6,
							color: GOLD,
							textTransform: 'uppercase'
						},
						children: 'Ochorus'
					}
				},
				{
					type: 'div',
					props: {
						style: { display: 'flex', flexDirection: 'column', gap: '20px' },
						children: [
							{
								type: 'div',
								props: {
									style: { fontFamily: 'serif', fontSize: 88, lineHeight: 1.05, color: PAPER },
									children: title
								}
							},
							{
								type: 'div',
								props: { style: { fontSize: 32, color: MUTED }, children: subtitle }
							}
						]
					}
				}
			]
		}
	};
}

async function render(name, title, subtitle) {
	const svg = await satori(card(title, subtitle), {
		width: 1200,
		height: 630,
		fonts: [
			{ name: 'serif', data: serif, weight: 700, style: 'normal' },
			{ name: 'sans', data: sans, weight: 400, style: 'normal' }
		]
	});
	const png = new Resvg(svg, { fitTo: { mode: 'width', value: 1200 } }).render().asPng();
	writeFileSync(resolve(OUT_DIR, `${name}.png`), png);
	console.log(`  ✓ og/${name}.png  (${title})`);
}

// The fixed card set — one per browse section, plus a generic default that the
// topic/plan detail pages and any other image-less page fall back to.
const CARDS = [
	['default', 'Ochorus', 'Free public-domain Christian classics'],
	['books', 'The Library', 'Free public-domain Christian books'],
	['sermons', 'Sermons', 'Classic sermons, free to read'],
	['plans', 'Reading Plans', 'Guided journeys through the classics'],
	['topics', 'Topics', 'Browse the library by theme'],
	['biographies', 'Biographies', 'The lives behind the classics']
];

mkdirSync(OUT_DIR, { recursive: true });
for (const [name, title, subtitle] of CARDS) {
	await render(name, title, subtitle);
}
console.log(`Wrote ${CARDS.length} cards to ${OUT_DIR}`);
