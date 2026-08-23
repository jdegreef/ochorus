/**
 * Generate one Open Graph share image (1200×630 PNG) per sermon.
 *
 * Output: frontend/static/og/sermons/<slug>.png — committed to the repo and
 * served as a static asset, like the pre-rasterized book covers. NOT part of
 * the build or CI; run it by hand after adding or retitling a sermon:
 *
 *     cd frontend && npm run og:sermons
 *
 * Always draws every card and writes only the ones whose BYTES changed. The
 * first version skipped any slug that already had a file, which kept the diff
 * clean but meant retitling a sermon silently shipped its old card — and the
 * fixture gate only checks that a card exists, so that would have sailed past
 * green CI. Rendering is deterministic (same fixtures and fonts in, same PNG
 * out, verified across two full runs), so comparing bytes gets the clean diff
 * without the staleness: adding one sermon still touches exactly one file.
 *
 * It also writes `og-manifest.json`: per slug, a digest of the INPUTS each card
 * was drawn from, so a gate can tell a stale card from a fresh one. Existence
 * was never the hard part — the book twins sat a design generation out of date
 * for months precisely because their gate could only see that a file was there,
 * and a share card is only ever seen by someone who is not us.
 *
 * TWO digests, because no single language can see both halves. `content` covers
 * the strings off the fixture (title, passage, preacher, year) and is recomputed
 * by `SermonShareCardTests` in Python; `art` covers the emblem this slug
 * resolves to, its drawing and the hue derived from it, and is recomputed by
 * `sermonCards.test.ts` in vitest, which is the side that can read the
 * catalogue. Neither can see a change to this script's own composition — only
 * re-running it can — so they are a floor, not a proof.
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
 * The policy and its reasoning are `generate-og.mjs`'s, inherited rather than
 * invented here: scrapers rarely read localized cards. A translated sermon
 * page therefore shares the English card — which is what every translated BOOK
 * page already does too, since all 89 of them carry a generated `.svg` cover
 * and that routes their og:image to the English `/covers/<slug>.png`.
 *
 * SOURCE OF TRUTH
 * The committed English sermon fixtures, not the API — this runs on a laptop
 * with no database, and the fixtures are what production is seeded from
 * anyway. `backend/library/tests_fixture.py` fails the build if a sermon in
 * those fixtures has no card here.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { channels } from '../src/lib/coverArt.ts';
// Two doors, and the split is load-bearing rather than cosmetic — see the
// header of emblems.ts. The art here, the slug->emblem assignment there.
import { emblemForSermon } from '../src/lib/emblemNames.ts';
import { EMBLEM_ART, emblemHue } from '../src/lib/emblems.ts';
import {
	BACKGROUND,
	GOLD,
	HEIGHT,
	MUTED,
	PAPER,
	WIDTH,
	drawCard,
	liftToContrast
} from './og-card.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og/sermons');
mkdirSync(OUT_DIR, { recursive: true });
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

const digest = (s) => createHash('sha256').update(s).digest('hex');

/** The strings off the fixture. Python recomputes this one. */
const contentDigest = (s) =>
	digest([s.title, s.scripture, s.author, s.year].join('\0'));

/**
 * The art this slug resolves to. Vitest recomputes this one.
 *
 * The emblem and its drawing, not the accent: the accent comes from
 * `liftToContrast`, which is this generator's own composition rather than
 * content, and neither gate claims to see composition change. What these catch
 * is a sermon reassigned to a different emblem, or a drawing edited.
 */
const artDigest = (emblem) => digest([emblem, EMBLEM_ART[emblem]].join('\0'));

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

const rows = sermons();
const manifest = {};
let wrote = 0;
for (const sermon of rows) {
	const out = resolve(OUT_DIR, `${sermon.slug}.png`);
	const emblem = emblemForSermon(sermon.slug);
	// Emblem hues are chosen for the app's light surfaces; on this near-black
	// ground the darker ones need brightening before they carry type at all.
	const accent = liftToContrast(emblemHue(emblem));
	manifest[sermon.slug] = { content: contentDigest(sermon), art: artDigest(emblem) };
	const png = await drawCard(card({ ...sermon, emblem, accent }));
	if (existsSync(out) && readFileSync(out).equals(png)) continue;
	writeFileSync(out, png);
	wrote += 1;
	console.log(`  ✓ og/sermons/${sermon.slug}.png  (${emblem}, ${accent})`);
}
// Written every run, not only when a card changes: the digests must describe
// the cards that are on disk now, or the gate would pass on a manifest that
// agrees with nothing.
writeFileSync(
	resolve(OUT_DIR, 'og-manifest.json'),
	JSON.stringify(
		{
			_comment:
				'GENERATED by npm run og:sermons. slug -> digests of what each card was ' +
				'drawn from, so the gates can tell a stale card from a fresh one.',
			cards: Object.fromEntries(
				Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b))
			)
		},
		null,
		'\t'
	) + '\n',
	'utf8'
);

console.log(
	`${rows.length} sermon cards drawn · ${wrote} written to ${OUT_DIR}` +
		(wrote ? '' : ' · all already current')
);
