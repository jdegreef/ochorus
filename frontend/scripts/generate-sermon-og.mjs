/**
 * Generate one Open Graph share image (1200×630 PNG) per sermon.
 *
 * Output: frontend/static/og/sermons/<slug>.png — committed to the repo and
 * served as a static asset, like the pre-rasterized book covers. NOT part of
 * the build or CI; run it by hand after adding or retitling a sermon:
 *
 *     cd frontend && npm run og:sermons              # fill the gaps
 *     cd frontend && npm run og:sermons -- --force   # redraw everything
 *
 * Gap-filling by default, like `generate_covers`: a run that redrew all 29
 * every time turned "I added one sermon" into a 29-file binary diff, and any
 * difference in installed fonts between two laptops into another one.
 *
 * Needs a Node that strips TypeScript types unprompted (>= 22.18), because it
 * reads the emblem catalogue straight out of `src/lib/emblems.ts`.
 *
 * WHY THIS EXISTS
 * A sermon page's og:image used to be the AUTHOR PORTRAIT, so all thirteen
 * Spurgeon sermons shared as the same photograph of Spurgeon — and a sermon by
 * an author with no portrait shared as nothing at all. Forwarding a link is how
 * this library actually spreads, so the share card is the one surface where
 * missing art costs readers.
 *
 * WHY A CARD AND NOT A COVER
 * Books are 3:4 portrait plates; a sermon is a twenty-minute read, not a
 * volume, and giving it the same silhouette would mis-sell its length and blur
 * the one instant cue that tells the two apart on a mixed shelf. So a sermon
 * gets a landscape card in the shared OG ground (scripts/og-card.mjs), wearing
 * the emblem it already wears everywhere else in the app.
 *
 * ENGLISH ONLY, ONE PER SLUG
 * The policy and the reasoning live in ./og-card.mjs, shared with the
 * browse-page cards. A translated sermon page shares the English card, which
 * is already true of every book.
 *
 * SOURCE OF TRUTH
 * The committed English sermon fixtures, not the API — this runs on a laptop
 * with no database, and the fixtures are what production is seeded from
 * anyway. `backend/library/tests_fixture.py` fails the build if a sermon in
 * those fixtures has no card here.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { channels } from '../src/lib/coverArt.ts';
import { EMBLEM_ART, emblemForSermon, emblemHue } from '../src/lib/emblems.ts';
import {
	BACKGROUND,
	GOLD,
	HEIGHT,
	MUTED,
	PAPER,
	WIDTH,
	liftToContrast,
	renderCard
} from './og-card.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og/sermons');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');

// ── The content ─────────────────────────────────────────────────────────────

/** Author slug → display name, from the shared authors fixture. */
function authorNames() {
	const rows = JSON.parse(readFileSync(resolve(CONTENT, 'authors.json'), 'utf8'));
	return new Map(rows.map((r) => [r.fields.slug, r.fields.name]));
}

/** Every English sermon row, in slug order. */
function sermons() {
	const names = authorNames();
	return readdirSync(resolve(CONTENT, 'sermons'))
		.filter((f) => f.endsWith('.en.json'))
		.sort()
		.flatMap((file) => JSON.parse(readFileSync(resolve(CONTENT, 'sermons', file), 'utf8')))
		.filter((row) => row.model === 'library.sermon')
		.map(({ fields }) => ({
			slug: fields.slug,
			title: fields.title,
			scripture: fields.scripture_ref,
			// The fixture's `author` is a natural key — ["author-slug"].
			author: names.get(fields.author[0]) ?? fields.author[0],
			year: fields.preached_on ? fields.preached_on.slice(0, 4) : ''
		}));
}

// ── The card ────────────────────────────────────────────────────────────────

/** The emblem, wrapped as a standalone SVG document satori can place as an image. */
function emblemUri(name) {
	const svg =
		`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none">${EMBLEM_ART[name]}</svg>`;
	return `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`;
}

/** `#rrggbb` at `alpha` — satori has no color-mix, so the tint is mixed here. */
function alpha(hex, a) {
	return `rgba(${channels(hex).join(', ')}, ${a})`;
}

/**
 * Title size by length. The card is a fixed 630px tall with no room to grow,
 * and the longest title in the library runs 40 characters ("Come Thou and All
 * Thy House into the Ark"), so the budget is set from that rather than from
 * measuring — the same greedy trade `BookCover` and `covers.py` make.
 */
function titleSize(title) {
	if (title.length <= 22) return 82;
	if (title.length <= 34) return 70;
	return 58;
}

/** A satori div. Most of this card is layout, so `box` rather than `text`. */
const box = (style, children) => ({ type: 'div', props: { style, children } });

function card({ title, scripture, author, year, emblem, accent }) {
	const byline = year ? `${author} · ${year}` : author;
	return {
		type: 'div',
		props: {
			style: {
				width: `${WIDTH}px`,
				height: `${HEIGHT}px`,
				display: 'flex',
				flexDirection: 'column',
				justifyContent: 'space-between',
				padding: '72px',
				background: BACKGROUND,
				fontFamily: 'sans'
			},
			children: [
				// Eyebrow: the wordmark, and what kind of thing this is. A reader
				// scanning a feed should know it is a sermon before reading the title.
				box({ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, [
					box({ fontSize: 30, letterSpacing: 6, color: GOLD }, 'OCHORUS'),
						// Muted, not the accent: on the eleven sermons whose emblem is
					// predominantly gold, an accent-coloured label sat on the same line
					// as the gold wordmark and the two read as one word. Gold is the
					// brand's, the accent is the sermon's own, and they stay apart.
					box({ fontSize: 26, letterSpacing: 6, color: MUTED }, 'SERMON')
				]),
				// flex: 1 rather than letting `space-between` push this to the foot —
				// with only two children that left a third of the card empty above the
				// scripture line and the whole composition sitting on the bottom edge.
				box({ display: 'flex', flex: 1, alignItems: 'center', gap: '56px' }, [
					// The words carry the card; the emblem is the anchor beside them.
					box({ display: 'flex', flexDirection: 'column', flex: 1, gap: '18px' }, [
						box({ fontSize: 30, letterSpacing: 2, color: accent }, scripture),
						box(
							{
								fontFamily: 'serif',
								fontSize: titleSize(title),
								lineHeight: 1.08,
								color: PAPER
							},
							title
						),
						box({ fontSize: 30, color: MUTED }, byline)
					]),
					box(
						{
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							flexShrink: 0,
							width: '290px',
							height: '290px',
							borderRadius: '999px',
							// The app's emblem chip recipe (app.css `.emblem-chip`): a wash of
							// the hue with a ring of it, art at 66%. Heavier here than on a
							// light surface, where 14% already reads.
							background: alpha(accent, 0.16),
							border: `2px solid ${alpha(accent, 0.4)}`
						},
						{ type: 'img', props: { src: emblemUri(emblem), width: 215, height: 215 } }
					)
				])
			]
		}
	};
}

// ── Run ─────────────────────────────────────────────────────────────────────

const force = process.argv.includes('--force');
const rows = sermons();
let wrote = 0;
for (const sermon of rows) {
	const out = resolve(OUT_DIR, `${sermon.slug}.png`);
	if (!force && existsSync(out)) continue;
	const emblem = emblemForSermon(sermon.slug);
	// Emblem hues are chosen for the app's light surfaces; on this near-black
	// ground the darker ones need brightening before they carry type at all.
	const accent = liftToContrast(emblemHue(emblem));
	await renderCard(card({ ...sermon, emblem, accent }), out);
	wrote += 1;
	console.log(`  ✓ og/sermons/${sermon.slug}.png  (${emblem}, ${accent})`);
}
console.log(
	`Wrote ${wrote} of ${rows.length} sermon cards to ${OUT_DIR}` +
		(force ? '' : ` · ${rows.length - wrote} already drawn (--force to redraw)`)
);
