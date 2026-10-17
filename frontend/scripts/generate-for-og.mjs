/**
 * Generate the Open Graph share images (1200×630 PNG) for the "Ochorus for …"
 * pages: one per group, and one for the /for/ index.
 *
 * Output: frontend/static/og/for/<slug>.png and og/for/index.png, and the French
 * cards under og/for/fr/ (the pages are written in both) — committed and
 * served as static assets, like the topic and sermon cards. NOT part of the
 * build or CI; run it by hand after adding a group or changing one's label,
 * tagline, accent or emblem:
 *
 *     cd frontend && npm run og:for
 *
 * A pastor forwarding /for/churches/ to the elders, or a mission agency posting
 * /for/missionaries/ in a newsletter, is exactly the share these pages exist
 * for, so each carries its group's identity — the curated accent and emblem
 * (`FOR_META`) — on the shared OG ground, in the topic card's layout.
 *
 * CONTENT SOURCE — all TypeScript, read directly
 * The label is `FOR_LINKS` ($lib/forLinks); the tagline, accent and emblem
 * are `FOR_META` and the index card's words `FOR_INDEX_CARD` ($lib/forMeta,
 * import-free on purpose so this script can read it). So both
 * halves of the manifest are recomputed by one gate, `forCards.test.ts`.
 *
 * THE MANIFEST (og-manifest.json)
 *   - `cards`        — per card, a digest of everything drawn on it (the
 *     CURATED accent, as stored, not the contrast-lifted one it draws with).
 *   - `composition`  — the bytes of this script + `og-card.mjs`.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EMBLEM_ART } from '../src/lib/emblems.ts';
import { FOR_EYEBROW, FOR_LINKS, FOR_LOCALES, forLabel } from '../src/lib/forLinks.ts';
import { FOR_META, forIndexCard, forTagline } from '../src/lib/forMeta.ts';
import {
	BACKGROUND,
	GOLD,
	HEIGHT,
	MUTED,
	PAPER,
	WIDTH,
	alpha,
	box,
	drawCard,
	emblemUri,
	liftToContrast
} from './og-card.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og/for');
mkdirSync(resolve(OUT_DIR, 'fr'), { recursive: true });

/** The app's emblem-chip recipe: a wash of the hue with a ring of it. */
function chip(emblem, accent, size) {
	return box(
		{
			display: 'flex',
			alignItems: 'center',
			justifyContent: 'center',
			flexShrink: 0,
			width: `${size}px`,
			height: `${size}px`,
			boxSizing: 'border-box',
			borderRadius: '999px',
			background: alpha(accent, 0.16),
			border: `2px solid ${alpha(accent, 0.4)}`
		},
		{ type: 'img', props: { src: emblemUri(EMBLEM_ART[emblem]), width: Math.round(size * 0.74), height: Math.round(size * 0.74) } }
	);
}

/** The wordmark row's right-hand words, per language. */
const FREE_CLASSICS = { en: 'FREE CLASSICS', fr: 'CLASSIQUES GRATUITS' };

/** The shared frame: wordmark row, then the text column beside `art`. */
function frame({ locale, eyebrow, eyebrowColor, title, titleSize, tagline, art }) {
	return box(
		{
			width: `${WIDTH}px`,
			height: `${HEIGHT}px`,
			// The padding sits inside the card: satori now lays boxes out
			// content-box, which pushed the art and the wordmark off its edge.
			boxSizing: 'border-box',
			display: 'flex',
			flexDirection: 'column',
			justifyContent: 'space-between',
			padding: '72px',
			background: BACKGROUND,
			fontFamily: 'sans'
		},
		[
			box({ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, [
				box({ fontSize: 30, letterSpacing: 6, color: GOLD }, 'OCHORUS'),
				box({ fontSize: 26, letterSpacing: 6, color: MUTED }, FREE_CLASSICS[locale])
			]),
			box({ display: 'flex', flex: 1, alignItems: 'center', gap: '56px' }, [
				box({ display: 'flex', flexDirection: 'column', flex: 1, gap: '18px' }, [
					box({ fontSize: 30, letterSpacing: 2, color: eyebrowColor }, eyebrow),
					box({ fontFamily: 'serif', fontSize: titleSize, lineHeight: 1.08, color: PAPER }, title),
					box({ fontSize: 30, lineHeight: 1.35, color: MUTED }, tagline)
				]),
				art
			])
		]
	);
}

/** Title size by length: "Missionaries" fits large, "Homeschool families" doesn't. */
const titleSize = (title) => (title.length <= 14 ? 92 : title.length <= 22 ? 76 : 62);

function groupCard(link, locale) {
	const { accent: curated, emblem } = FOR_META[link.slug];
	// Tuned for the app's light chips; brightened to carry type on the dark ground.
	const accent = liftToContrast(curated);
	const label = forLabel(link, locale);
	return frame({
		locale,
		eyebrow: FOR_EYEBROW[locale],
		eyebrowColor: accent,
		title: label,
		titleSize: titleSize(label),
		tagline: forTagline(link.slug, locale),
		art: chip(emblem, accent, 290)
	});
}

function indexCard(locale) {
	const card = forIndexCard(locale);
	// Every group's emblem, three by three.
	const tiles = FOR_LINKS.map((l) => {
		const m = FOR_META[l.slug];
		return chip(m.emblem, liftToContrast(m.accent), 92);
	});
	return frame({
		locale,
		eyebrow: card.eyebrow,
		eyebrowColor: GOLD,
		title: card.title,
		titleSize: 76,
		tagline: card.tagline,
		art: box({ display: 'flex', flexWrap: 'wrap', width: '320px', gap: '22px', flexShrink: 0 }, tiles)
	});
}

const digest = (s) => createHash('sha256').update(s).digest('hex');

/** The drawing code, as bytes — any edit stales the manifest by one re-run. */
const compositionDigest = () =>
	digest(
		[resolve(HERE, 'generate-for-og.mjs'), resolve(HERE, 'og-card.mjs')]
			.map((f) => readFileSync(f, 'utf8'))
			.join('\0')
	);

/** Everything a group card is drawn from. `forCards.test.ts` mirrors this.
 *  English leads with the words alone (its digests predate the French cards);
 *  any other language adds its eyebrow. */
const groupDigest = (link, locale = 'en') => {
	const { accent, emblem } = FOR_META[link.slug];
	const words = [forLabel(link, locale), forTagline(link.slug, locale)];
	if (locale !== 'en') words.unshift(FOR_EYEBROW[locale]);
	return digest([...words, emblem, EMBLEM_ART[emblem], accent].join('\0'));
};

/** The index card: its words, and every group's art in order. */
const indexDigest = (locale = 'en') => {
	const card = forIndexCard(locale);
	return digest([card.eyebrow, card.title, card.tagline, ...FOR_LINKS.map((l) => groupDigest(l, locale))].join('\0'));
};

// ── Run ─────────────────────────────────────────────────────────────────────

/** A card's name: its file under og/for/, without .png. */
const cardName = (name, locale) => (locale === 'en' ? name : `${locale}/${name}`);

const cards = FOR_LOCALES.flatMap((locale) => [
	...FOR_LINKS.map((l) => [cardName(l.slug, locale), groupCard(l, locale), groupDigest(l, locale)]),
	[cardName('index', locale), indexCard(locale), indexDigest(locale)]
]);
let wrote = 0;
for (const [name, node] of cards) {
	const out = resolve(OUT_DIR, `${name}.png`);
	const png = await drawCard(node);
	if (existsSync(out) && readFileSync(out).equals(png)) continue;
	writeFileSync(out, png);
	wrote += 1;
	console.log(`  ✓ og/for/${name}.png`);
}
writeFileSync(
	resolve(OUT_DIR, 'og-manifest.json'),
	JSON.stringify(
		{
			_comment:
				'GENERATED by npm run og:for. card -> digest of what it was drawn from, ' +
				'so forCards.test.ts can tell a stale card from a fresh one.',
			composition: compositionDigest(),
			cards: Object.fromEntries(cards.map(([name, , d]) => [name, d]).sort(([a], [b]) => a.localeCompare(b)))
		},
		null,
		'\t'
	) + '\n',
	'utf8'
);
console.log(`${cards.length} cards drawn · ${wrote} written to ${OUT_DIR}` + (wrote ? '' : ' · all already current'));
