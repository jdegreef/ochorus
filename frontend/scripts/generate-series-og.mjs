/**
 * Generate one Open Graph share image (1200×630 PNG) per book SERIES.
 *
 * Output: frontend/static/og/series/<slug>.png + og-manifest.json — committed
 * and served as static assets, like the topic and sermon cards. NOT part of
 * the build or CI; run it by hand after adding a series or a volume, or
 * changing a series' title, tagline or a volume's cover:
 *
 *     cd frontend && npm run og:series
 *
 * WHY: a series page used to share its first volume's card, so a link to The
 * Lamplighters of Gloamhaven forwarded as "Fire Against the Dark" — one book,
 * not the series of six. This card names the series, carries its promise
 * line, and fans out its first covers.
 *
 * Same family as the topic card (`og-card.mjs`'s ground, eyebrow and type
 * scale), in the series' own accent (`seriesMeta(slug).accent`, lifted for
 * contrast on the dark ground).
 *
 * THE MANIFEST: per series `content` (the strings, volume count and cover
 * bytes, `series-og-content.mjs`) and `accent`; once, `composition` (this
 * script + its helpers). `src/lib/seriesCards.test.ts` recomputes all three.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

import { seriesMeta } from '../src/lib/emblemNames.ts';
import { BACKGROUND, GOLD, HEIGHT, MUTED, PAPER, WIDTH, box, drawCard, liftToContrast } from './og-card.mjs';
import { STATIC, compositionDigest, contentDigest, coversOf, seriesCards } from './series-og-content.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, '../static/og/series');
mkdirSync(OUT_DIR, { recursive: true });

const COVER_W = 210;
const COVER_H = 315;

function titleSize(title) {
	if (title.length <= 18) return 84;
	if (title.length <= 30) return 68;
	return 56;
}

/** The promise line, else the description's opening, trimmed on a word. */
function lineFor({ tagline, description }) {
	const text = tagline || description;
	const LIMIT = 110;
	if (text.length <= LIMIT) return text;
	const cut = text.slice(0, LIMIT);
	return cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;—-]+$/, '') + '…';
}

/** A cover as a JPEG data URI satori can place (it reads no WebP). */
async function coverUri(path) {
	const jpg = await sharp(resolve(STATIC, path.slice(1)))
		.resize(COVER_W * 2, COVER_H * 2, { fit: 'cover' })
		.jpeg({ quality: 82 })
		.toBuffer();
	return `data:image/jpeg;base64,${jpg.toString('base64')}`;
}

function card({ title, line, count, covers, accent }) {
	// A fan: volume one in front, two and three turned out behind it.
	const SLOTS = [
		{ x: 0, y: 0, turn: 0 },
		{ x: -100, y: 22, turn: -8 },
		{ x: 100, y: 22, turn: 8 }
	];
	const fan = covers
		.map((src, i) => ({ src, ...SLOTS[i] }))
		.reverse()
		.map(({ src, x, y, turn }) => ({
			type: 'img',
			props: {
				src,
				width: COVER_W,
				height: COVER_H,
				style: {
					position: 'absolute',
					left: `${190 + x - COVER_W / 2}px`,
					top: `${30 + y}px`,
					transform: `rotate(${turn}deg)`,
					borderRadius: '10px',
					boxShadow: '0 18px 40px rgba(0, 0, 0, 0.55)'
				}
			}
		}));
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
				boxSizing: 'border-box',
				background: BACKGROUND,
				fontFamily: 'sans'
			},
			children: [
				box({ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, [
					box({ fontSize: 30, letterSpacing: 6, color: GOLD }, 'OCHORUS'),
					box({ fontSize: 26, letterSpacing: 6, color: MUTED }, 'BOOK SERIES')
				]),
				box({ display: 'flex', flex: 1, alignItems: 'center', gap: '40px' }, [
					box({ display: 'flex', flexDirection: 'column', flex: 1, gap: '18px' }, [
						box(
							{ fontSize: 28, letterSpacing: 2, color: accent },
							count === 1 ? '1 BOOK' : `${count} BOOKS`
						),
						box({ fontFamily: 'serif', fontSize: titleSize(title), lineHeight: 1.08, color: PAPER }, title),
						box({ fontSize: 30, lineHeight: 1.35, color: MUTED }, line)
					]),
					box(
						{
							display: 'flex',
							position: 'relative',
							flexShrink: 0,
							width: '380px',
							height: '380px'
						},
						fan
					)
				])
			]
		}
	};
}

const cards = seriesCards();
const manifest = {};
let wrote = 0;
for (const [slug, c] of Object.entries(cards)) {
	const { accent: curated } = seriesMeta(slug);
	const covers = await Promise.all(coversOf(c).map((b) => coverUri(b.cover)));
	manifest[slug] = { content: contentDigest(c), accent: curated };
	const png = await drawCard(
		card({ title: c.title, line: lineFor(c), count: c.books.length, covers, accent: liftToContrast(curated) })
	);
	const out = resolve(OUT_DIR, `${slug}.png`);
	if (existsSync(out) && readFileSync(out).equals(png)) continue;
	writeFileSync(out, png);
	wrote += 1;
	console.log(`  ✓ og/series/${slug}.png  (${c.books.length} books, ${curated})`);
}
writeFileSync(
	resolve(OUT_DIR, 'og-manifest.json'),
	JSON.stringify(
		{
			_comment:
				'GENERATED by npm run og:series. slug -> what each card was drawn from, ' +
				'so src/lib/seriesCards.test.ts can tell a stale card from a fresh one.',
			composition: compositionDigest(),
			cards: Object.fromEntries(Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)))
		},
		null,
		'\t'
	) + '\n',
	'utf8'
);
console.log(`${Object.keys(cards).length} series cards drawn · ${wrote} written to ${OUT_DIR}`);
