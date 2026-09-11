/**
 * Generate one Open Graph share image (1200×630 PNG) per TOPIC.
 *
 * Output: frontend/static/og/topics/<slug>.png — committed and served as a
 * static asset, exactly like the sermon cards. NOT part of the build or CI;
 * run it by hand after adding, retitling or re-accenting a topic:
 *
 *     cd frontend && npm run og:topics
 *
 * WHY THIS EXISTS
 * Every topic page used to share the ONE generic `/og/topics.png` ("Browse the
 * library by theme"), so a link to The Puritans and a link to On Prayer
 * forwarded into a chat as the same anonymous card. A topic already has its own
 * identity in the app — a curated accent + a hand-drawn emblem (`TOPIC_META`) —
 * and this puts that identity on the share card, the one surface a link
 * carries into places we don't control.
 *
 * SAME FAMILY AS THE SERMON CARD
 * Drawn on the shared OG ground (`og-card.mjs`) with the same eyebrow, emblem
 * chip and type scale, so a forwarded Ochorus link is recognisable whatever it
 * points at. The one deliberate difference from the sermon card: a topic wears
 * its CURATED accent (`topicMeta(slug).accent`), not a hue derived from its
 * emblem — that curated hue is the colour the topic IS across the app.
 *
 * CONTENT SOURCE — one root, bridged
 * Title / description / scripture live in `library/topic_seed.py` (a topic is
 * one Topic row + a TopicTranslation, and its English text is authored there).
 * This script has no Django and no DB, so it shells out to
 * `backend/scripts/export_topic_cards.py`, which `ast`-parses that module to
 * JSON. The accent + emblem come from the TypeScript catalogue (`emblemNames` /
 * `emblems`), read directly under Node's type stripping.
 *
 * ENGLISH ONLY, ONE PER SLUG
 * Inherited from `generate-og.mjs` / `generate-sermon-og.mjs`: scrapers rarely
 * read localized cards, so a translated topic page shares the English card.
 *
 * THE MANIFEST (og-manifest.json) — staleness, split by who can recompute it
 *   - `content`  — the strings off topic_seed.py. Recomputed by
 *     `TopicShareCardTests` (Python), the side that can read that module.
 *   - `art`      — what the catalogue says the topic wears: the emblem, its
 *     drawing, and the curated accent. Recomputed by `topicCards.test.ts`.
 *   - `composition` — the bytes of this script + `og-card.mjs`, so a design
 *     change that restyles every card can't slip past with content unchanged.
 * The line is INPUTS, not output: a change in satori/resvg is still invisible.
 *
 * Needs a Node that strips TypeScript types unprompted (>= 22.18), and python3
 * on PATH for the content export.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { channels } from '../src/lib/coverArt.ts';
import { topicMeta } from '../src/lib/emblemNames.ts';
import { EMBLEM_ART } from '../src/lib/emblems.ts';
import { BACKGROUND, GOLD, HEIGHT, MUTED, PAPER, WIDTH, drawCard, liftToContrast } from './og-card.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og/topics');
mkdirSync(OUT_DIR, { recursive: true });
const EXPORT = resolve(HERE, '../../backend/scripts/export_topic_cards.py');

// ── The content ─────────────────────────────────────────────────────────────

/** slug → {title, description, scripture_ref, scripture_text}, from topic_seed.py. */
function topicCards() {
	const json = execFileSync('python3', [EXPORT], { encoding: 'utf8', maxBuffer: 1 << 22 });
	return JSON.parse(json);
}

// ── The card ────────────────────────────────────────────────────────────────

/** The emblem, wrapped as a standalone SVG document satori can place as an image. */
function emblemUri(name) {
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none">${EMBLEM_ART[name]}</svg>`;
	return `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`;
}

/** `#rrggbb` at `alpha` — satori has no color-mix, so the tint is mixed here. */
function alpha(hex, a) {
	return `rgba(${channels(hex).join(', ')}, ${a})`;
}

/**
 * Title size by length. Topic titles are short (the longest, "To the Ends of
 * the Earth" and "The Wesleys & Early Methodism", run ~28 chars), so the budget
 * is generous — the same greedy trade the sermon card makes.
 */
function titleSize(title) {
	if (title.length <= 16) return 92;
	if (title.length <= 26) return 76;
	return 62;
}

/**
 * The tagline is a full sentence or two; the card has room for a couple of
 * lines beside a big title, not a paragraph. Trim on a word boundary so a long
 * description reads as a lede, not a clipped fragment.
 */
function taglineFor(description) {
	const LIMIT = 118;
	if (description.length <= LIMIT) return description;
	const cut = description.slice(0, LIMIT);
	// Cut at the last word boundary, then drop a dangling comma/semicolon/dash
	// before the ellipsis (the slice already can't end in whitespace).
	return cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;—-]+$/, '') + '…';
}

/** A satori div. Most of this card is layout, so `box` rather than `text`. */
const box = (style, children) => ({ type: 'div', props: { style, children } });

const digest = (s) => createHash('sha256').update(s).digest('hex');

/** The drawing code, as bytes — any edit stales the manifest by one re-run. */
const compositionDigest = () =>
	digest(
		[resolve(HERE, 'generate-topic-og.mjs'), resolve(HERE, 'og-card.mjs')]
			.map((f) => readFileSync(f, 'utf8'))
			.join('\0')
	);

/** The strings off topic_seed.py. Python (`TopicShareCardTests`) recomputes this. */
const contentDigest = (c) =>
	digest([c.title, c.description, c.scripture_ref, c.scripture_text].join('\0'));

/** What the catalogue says the topic wears. `topicCards.test.ts` recomputes this. */
const artDigest = (emblem, accent) => digest([emblem, EMBLEM_ART[emblem], accent].join('\0'));

function card({ title, tagline, scripture_ref, emblem, accent }) {
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
				box({ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, [
					box({ fontSize: 30, letterSpacing: 6, color: GOLD }, 'OCHORUS'),
					box({ fontSize: 26, letterSpacing: 6, color: MUTED }, 'TOPIC')
				]),
				box({ display: 'flex', flex: 1, alignItems: 'center', gap: '56px' }, [
					box(
						{ display: 'flex', flexDirection: 'column', flex: 1, gap: '18px' },
						// A topic without a scripture epigraph drops the line entirely
						// rather than leaving an empty node (satori rejects a childless
						// div without an explicit display).
						[
							scripture_ref &&
								box({ fontSize: 30, letterSpacing: 2, color: accent }, scripture_ref),
							box(
								{ fontFamily: 'serif', fontSize: titleSize(title), lineHeight: 1.08, color: PAPER },
								title
							),
							box({ fontSize: 30, lineHeight: 1.35, color: MUTED }, tagline)
						].filter(Boolean)
					),
					box(
						{
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							flexShrink: 0,
							width: '290px',
							height: '290px',
							borderRadius: '999px',
							// The app's emblem-chip recipe (app.css `.emblem-chip`): a wash of
							// the hue with a ring of it, art at ~74%.
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

const cards = topicCards();
const manifest = {};
let wrote = 0;
for (const [slug, content] of Object.entries(cards)) {
	const out = resolve(OUT_DIR, `${slug}.png`);
	const { emblem, accent: curated } = topicMeta(slug);
	// The curated accent was tuned for the app's light chips; on this near-black
	// ground the darker ones need brightening before they carry type.
	const accent = liftToContrast(curated);
	manifest[slug] = { content: contentDigest(content), art: artDigest(emblem, curated) };
	const png = await drawCard(
		card({ title: content.title, tagline: taglineFor(content.description), scripture_ref: content.scripture_ref, emblem, accent })
	);
	if (existsSync(out) && readFileSync(out).equals(png)) continue;
	writeFileSync(out, png);
	wrote += 1;
	console.log(`  ✓ og/topics/${slug}.png  (${emblem}, ${curated})`);
}
writeFileSync(
	resolve(OUT_DIR, 'og-manifest.json'),
	JSON.stringify(
		{
			_comment:
				'GENERATED by npm run og:topics. slug -> digests of what each card was ' +
				'drawn from, so the gates can tell a stale card from a fresh one.',
			composition: compositionDigest(),
			cards: Object.fromEntries(Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)))
		},
		null,
		'\t'
	) + '\n',
	'utf8'
);

console.log(
	`${Object.keys(cards).length} topic cards drawn · ${wrote} written to ${OUT_DIR}` +
		(wrote ? '' : ' · all already current')
);
