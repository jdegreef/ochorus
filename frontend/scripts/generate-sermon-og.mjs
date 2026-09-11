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
 * without the staleness: adding one sermon redraws one PNG. It does also
 * rewrite the shared manifest below, so two branches adding a sermon at once
 * touch one file in common — sorted keys keep that to a line each.
 *
 * It also writes `og-manifest.json`: digests of the INPUTS each card was drawn
 * from, so a gate can tell a stale card from a fresh one. Existence was never
 * the hard part — the book twins sat a design generation out of date for months
 * precisely because their gate could only see that a file was there, and a share
 * card is only ever seen by someone who is not us.
 *
 * THREE digests, split by who can recompute them.
 *
 *   - `content` — the strings off the fixture: title, passage, preacher, year.
 *     Recomputed by `SermonShareCardTests` in Python.
 *   - `art` — what the catalogue says this slug wears: the emblem, its drawing,
 *     and the hue derived from them. Recomputed by `sermonCards.test.ts`, the
 *     side that can read a TypeScript catalogue. The hue is in because the rule
 *     that produces it (`MIN_ACCENT_SATURATION`) lives in the catalogue: moving
 *     it repaints the passage line on cards whose art never changed.
 *   - `composition` — the bytes of this script and `og-card.mjs`. The book
 *     twins' gate stops short of this and says so; theirs is the very failure
 *     it declines to catch. Editing `GOLD` while working on `og:pages` restyles
 *     all 29 sermon cards, and without this every gate stays green.
 *
 * The line is INPUTS, not output: nothing here re-derives the PNG, so a change
 * in satori or resvg is still invisible. A floor, not a proof.
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
 * ENGLISH BY DEFAULT, WITH NAMED EXCEPTIONS
 * The default and its reasoning are `generate-og.mjs`'s, inherited rather than
 * invented here: scrapers rarely read localized cards, so a translated sermon
 * page shares the English card — which is what every translated BOOK page does
 * too, routing its og:image to the English `/covers/<slug>.png`. The exceptions
 * are `SERMON_OG_LOCALES` (src/lib/sermonOgLocales.ts): each locale there draws
 * its OWN card per translated sermon at `/og/sermons/<lang>/<slug>.png` (French
 * title, French passage), and the reader page points its og:image there. That
 * list is the single source of truth — this script and the page both read it —
 * and a locale on it must have a card for every one of its translated sermons
 * (the gates enforce it), or the localized og:image 404s.
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
// The locales that ship their OWN sermon cards instead of the English one — the
// single source of truth the reader page reads too, so the two cannot drift.
import { SERMON_OG_LOCALES } from '../src/lib/sermonOgLocales.ts';
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

/** Every sermon row for one language, in slug order. */
function sermonsFor(lang) {
	const names = authorNames();
	return readdirSync(resolve(CONTENT, 'sermons'))
		.filter((f) => f.endsWith(`.${lang}.json`))
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

/**
 * The drawing code, as bytes. Any edit to either file — including a comment —
 * stales the manifest, which costs one idempotent re-run and buys the one class
 * of staleness that actually bit this repo.
 */
const compositionDigest = () =>
	digest(
		[resolve(HERE, 'generate-sermon-og.mjs'), resolve(HERE, 'og-card.mjs')]
			.map((f) => readFileSync(f, 'utf8'))
			.join('\0')
	);

/** The strings off the fixture. Python recomputes this one. */
const contentDigest = (s) =>
	digest([s.title, s.scripture, s.author, s.year].join('\0'));

/**
 * What the catalogue says this slug wears. Vitest recomputes this one.
 *
 * `emblemHue` and not the final accent: the hue is the catalogue's answer, so a
 * change to its saturation floor belongs here, while `liftToContrast` is this
 * card's treatment and belongs in `composition` with the rest of the drawing.
 */
const artDigest = (emblem) => digest([emblem, EMBLEM_ART[emblem], emblemHue(emblem)].join('\0'));

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

let wrote = 0;

/** Draw one sermon's card to `out`, writing only when the bytes changed. */
async function render(sermon, out, label) {
	const emblem = emblemForSermon(sermon.slug);
	// Emblem hues are chosen for the app's light surfaces; on this near-black
	// ground the darker ones need brightening before they carry type at all.
	const accent = liftToContrast(emblemHue(emblem));
	const png = await drawCard(card({ ...sermon, emblem, accent }));
	if (!(existsSync(out) && readFileSync(out).equals(png))) {
		writeFileSync(out, png);
		wrote += 1;
		console.log(`  ✓ ${label}  (${emblem}, ${accent})`);
	}
	return { content: contentDigest(sermon), art: artDigest(emblem) };
}

const sorted = (obj) =>
	Object.fromEntries(Object.entries(obj).sort(([a], [b]) => a.localeCompare(b)));

// English: one card per slug at /og/sermons/<slug>.png — the default every
// translated page shares unless its locale opts into its own below.
const rows = sermonsFor('en');
const cards = {};
for (const sermon of rows) {
	cards[sermon.slug] = await render(sermon, resolve(OUT_DIR, `${sermon.slug}.png`), `og/sermons/${sermon.slug}.png`);
}

// Localized: the deliberate exceptions in SERMON_OG_LOCALES each draw their own
// card per translated sermon at /og/sermons/<lang>/<slug>.png, so a forwarded
// French link shows a French title. Kept in a SEPARATE manifest block from
// `cards`, whose key set the English gate pins exactly.
const localized = {};
for (const lang of SERMON_OG_LOCALES) {
	const dir = resolve(OUT_DIR, lang);
	mkdirSync(dir, { recursive: true });
	const langCards = {};
	for (const sermon of sermonsFor(lang)) {
		langCards[sermon.slug] = await render(sermon, resolve(dir, `${sermon.slug}.png`), `og/sermons/${lang}/${sermon.slug}.png`);
	}
	localized[lang] = sorted(langCards);
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
				'drawn from, so the gates can tell a stale card from a fresh one. ' +
				'`cards` is the English set (one per slug); `localized` holds the ' +
				'per-language cards for the SERMON_OG_LOCALES exceptions.',
			composition: compositionDigest(),
			cards: sorted(cards),
			localized
		},
		null,
		'\t'
	) + '\n',
	'utf8'
);

const localizedCount = Object.values(localized).reduce((n, c) => n + Object.keys(c).length, 0);
console.log(
	`${rows.length} English + ${localizedCount} localized sermon cards drawn · ` +
		`${wrote} written to ${OUT_DIR}` +
		(wrote ? '' : ' · all already current')
);
