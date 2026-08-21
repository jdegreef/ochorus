/**
 * Generate branded Open Graph share images (1200×630 PNG) for the browse/list
 * pages and the topic/plan detail pages, which otherwise ship no og:image.
 *
 * Output: frontend/static/og/<name>.png — committed to the repo and served as
 * static assets (like the pre-rasterized book covers). This script is NOT part
 * of the build or CI; run it by hand when the card set or branding changes:
 *
 *     cd frontend && npm run og:pages
 *
 * The ground, palette and faces come from ./og-card.mjs, shared with
 * generate-sermon-og.mjs so every Ochorus share card reads as the same family.
 *
 * og:image text is English only (social scrapers rarely read localized cards);
 * the same image serves every locale of a page.
 */
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { BACKGROUND, GOLD, HEIGHT, MUTED, PAPER, WIDTH, renderCard } from './og-card.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og');

/** One card: gold OCHORUS wordmark, big serif title, muted subtitle. */
function card(title, subtitle) {
	return {
		type: 'div',
		props: {
			style: {
				width: `${WIDTH}px`,
				height: `${HEIGHT}px`,
				display: 'flex',
				flexDirection: 'column',
				justifyContent: 'space-between',
				padding: '80px',
				background: BACKGROUND,
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
	await renderCard(card(title, subtitle), resolve(OUT_DIR, `${name}.png`));
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

for (const [name, title, subtitle] of CARDS) {
	await render(name, title, subtitle);
}
console.log(`Wrote ${CARDS.length} cards to ${OUT_DIR}`);
