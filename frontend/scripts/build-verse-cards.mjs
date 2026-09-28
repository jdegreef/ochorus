/**
 * Draw a share card for every prerendered scripture VERSE page.
 *
 * Runs as `postbuild`, after `build-share-cards.mjs`:
 *
 *     npm run build                                   # vite build, then both
 *     node scripts/build-verse-cards.mjs [buildDir]   # by hand; default ./build
 *
 * WHAT IT IS
 * A verse page is the one a reader shares to say "look at this verse", and it
 * used to preview as the house card. Its card is the verse itself, set large in
 * Fraunces with its reference, beside a fan of the classics that treat it and
 * a line saying how many chapters do — the page's whole argument, at a glance.
 *
 * WHY AT BUILD, NOT COMMITTED
 * Which verses have a page is decided by a floor on the server, and moves as the
 * library grows. Committed, ~900 cards (~40 MB) would need a manifest and a
 * staleness gate; drawn here they cannot go stale and cannot be missing. The
 * same bargain `build-share-cards.mjs` makes, for the same reason.
 *
 * THE BUILD IS THE SOURCE OF TRUTH. Each verse page carries the API response it
 * was rendered from (SvelteKit inlines a load's `fetch` as a
 * `data-sveltekit-fetched` script), so the card is drawn from exactly what the
 * page shows — no second trip to the API, which the prerender crawl already
 * loads heavily. A citing book's cover is the `Book.image` its own prerendered
 * English page names. A page this cannot read gets the house card, and says so:
 * a missing card must not fail a deploy.
 *
 * WHY SATORI: English-only text (the ASV), so no complex shaping is needed, and
 * satori (+ sharp's librsvg) run anywhere Node does — no browser on the build machine. It
 * cannot read variable woff2, so the brand faces are vendored as static
 * instances under `scripts/fonts` (see its LICENSE).
 */
import satori from 'satori';
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { LANDSCAPE_HEIGHT as H, LANDSCAPE_WIDTH as W } from '../src/lib/coverArt.ts';
import { verseCardUrl, verseData, verseType } from '../src/lib/verseCard.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const FALLBACK = '/og/default.png';

const PAPER = 'linear-gradient(180deg, #faf6ef 0%, #f1e8d8 100%)';
const INK = '#221c14';
const GOLD = '#9c6f1e';
const MUTED = '#6d6152';
const RULE = '#d9c29a';

/** The fan: up to three citing covers, the first-cited on top in the middle. */
const COVER_H = 200;
const FAN = [
	{ left: 90, top: 16, rotate: 0 },
	{ left: 15, top: 36, rotate: -9 },
	{ left: 165, top: 36, rotate: 9 }
];
/** Drawn back to front, so the middle cover lands on top. */
const PAINT_ORDER = [1, 2, 0];

// ── Reading the build ───────────────────────────────────────────────────────

const LD = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;

/** Book slug → the cover its English page names, as a file in the build. */
function covers(build) {
	const found = new Map();
	const books = join(build, 'books');
	if (!existsSync(books)) return found;
	for (const slug of readdirSync(books)) {
		const page = join(books, slug, 'index.html');
		if (!existsSync(page)) continue;
		for (const [, json] of readFileSync(page, 'utf8').matchAll(LD)) {
			try {
				const ld = JSON.parse(json);
				if (ld['@type'] !== 'Book' || !ld.image) continue;
				const file = join(build, new URL(ld.image).pathname);
				if (existsSync(file)) found.set(slug, file);
			} catch {
				/* not this block */
			}
		}
	}
	return found;
}

/** Every prerendered verse page: scripture/<book>/<chapter>/<verse>/index.html. */
function versePages(build) {
	const root = join(build, 'scripture');
	if (!existsSync(root)) return [];
	const dirs = (p) => readdirSync(p, { withFileTypes: true }).filter((e) => e.isDirectory());
	return dirs(root).flatMap((b) =>
		dirs(join(root, b.name)).flatMap((c) =>
			dirs(join(root, b.name, c.name))
				.map((v) => join(root, b.name, c.name, v.name, 'index.html'))
				.filter(existsSync)
		)
	);
}

// ── Drawing ─────────────────────────────────────────────────────────────────

/** The translation's short name, from the version the page itself shows —
 *  never assumed, so a card cannot credit one Bible with another's words. */
const SHORT = { 'American Standard Version': 'ASV' };
const versionLabel = (version) => SHORT[version] ?? version ?? '';

const h = (type, style, children, extra = {}) => ({ type, props: { style, children, ...extra } });

function layout(page, fanned) {
	const { text, size } = verseType(page.text);
	const cited =
		page.citing_count === 1 ? 'Cited in 1 chapter' : `Cited in ${page.citing_count} chapters`;
	return h(
		'div',
		{
			width: W,
			height: H,
			display: 'flex',
			position: 'relative',
			background: PAPER,
			fontFamily: 'Hanken'
		},
		[
			h(
				'div',
				{ position: 'absolute', left: 72, top: 58, fontSize: 20, letterSpacing: 6.4, color: GOLD },
				'OCHORUS'
			),
			h(
				'div',
				{
					position: 'absolute',
					left: 72,
					top: 110,
					width: fanned ? 690 : 1056,
					height: 400,
					display: 'flex',
					flexDirection: 'column',
					justifyContent: 'center'
				},
				[
					h(
						'div',
						{ fontFamily: 'Fraunces', fontSize: 120, lineHeight: 0.6, height: 44, color: RULE },
						'“'
					),
					h(
						'div',
						{
							fontFamily: 'Fraunces',
							fontSize: size,
							lineHeight: 1.22,
							letterSpacing: -0.3,
							color: INK
						},
						text
					),
					h('div', { display: 'flex', alignItems: 'baseline', marginTop: 26 }, [
						h(
							'div',
							{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 34, color: GOLD },
							page.reference
						),
						h('div', { fontSize: 18, color: MUTED, marginLeft: 16 }, versionLabel(page.version))
					])
				]
			),
			...(fanned
				? [
						h(
							'div',
							{
								position: 'absolute',
								left: 790,
								top: 400,
								width: 370,
								display: 'flex',
								justifyContent: 'center',
								fontSize: 20,
								color: '#4a4035'
							},
							`${cited} of the classics`
						)
					]
				: []),
			h('div', {
				position: 'absolute',
				left: 40,
				right: 40,
				top: 544,
				height: 3,
				background: RULE
			}),
			h(
				'div',
				{ position: 'absolute', left: 72, top: 574, fontSize: 19, color: MUTED },
				'Read what the great Christian classics say about it · ochorus.com'
			)
		]
	);
}

/** Where the fan sits on the card: its box's left/top. */
const FAN_LEFT = 810;
const FAN_TOP = 120;
/** Room around a cover for its shadow and its rotation. */
const BLEED = 28;

/**
 * One cover in its fan slot, ready to composite: at the fan's height and ITS
 * OWN aspect (a designed cover keeps its byline at the edges — see
 * build-share-cards), rounded, shadowed and turned. Composited by sharp rather
 * than drawn by satori, which decoded every embedded cover again for each of
 * the ~900 cards; a book cited by forty verses is now drawn once per slot.
 */
const fanCache = new Map();
function fanPiece(file, slot) {
	const key = `${slot}|${file}`;
	if (!fanCache.has(key)) {
		fanCache.set(
			key,
			(async () => {
				const { width = 3, height = 4 } = await sharp(file).metadata();
				const w = Math.round((COVER_H * width) / height);
				const round = `<svg width="${w}" height="${COVER_H}"><rect width="${w}" height="${COVER_H}" rx="4" fill="#fff"/></svg>`;
				const cover = await sharp(file)
					.resize(w, COVER_H, { fit: 'fill' })
					.composite([{ input: Buffer.from(round), blend: 'dest-in' }])
					.png()
					.toBuffer();
				const shade = `<svg width="${w + 2 * BLEED}" height="${COVER_H + 2 * BLEED}"><rect x="${BLEED}" y="${BLEED + 10}" width="${w}" height="${COVER_H}" rx="4" fill="rgb(60,40,10)" fill-opacity=".35"/></svg>`;
				const shadow = await sharp(Buffer.from(shade)).blur(10).png().toBuffer();
				const piece = await sharp(shadow)
					.composite([{ input: cover, left: BLEED, top: BLEED }])
					.png()
					.toBuffer();
				// A second pipeline: within one, sharp rotates BEFORE it composites,
				// which turned the shadow and left the cover square on top of it.
				const turned = await sharp(piece)
					.rotate(FAN[slot].rotate, { background: { r: 0, g: 0, b: 0, alpha: 0 } })
					.png()
					.toBuffer({ resolveWithObject: true });
				// Turning grows the canvas about its centre, which is the cover's.
				const cx = FAN_LEFT + FAN[slot].left + 75;
				const cy = FAN_TOP + FAN[slot].top + COVER_H / 2;
				return {
					input: turned.data,
					left: Math.round(cx - turned.info.width / 2),
					top: Math.round(cy - turned.info.height / 2)
				};
			})()
		);
	}
	return fanCache.get(key);
}

let fonts;
function loadFonts() {
	const face = (file) => readFileSync(resolve(HERE, 'fonts', file));
	return (fonts ??= [
		{ name: 'Fraunces', data: face('Fraunces-Regular.ttf'), weight: 400, style: 'normal' },
		{ name: 'Fraunces', data: face('Fraunces-Italic.ttf'), weight: 400, style: 'italic' },
		{ name: 'Hanken', data: face('HankenGrotesk-Medium.ttf'), weight: 500, style: 'normal' }
	]);
}

async function draw(page, coverFiles) {
	const books = [...new Set(page.passages.map((p) => p.book_slug))].filter((s) =>
		coverFiles.has(s)
	);
	const fan = books.slice(0, FAN.length).map((s) => coverFiles.get(s));
	const svg = await satori(layout(page, fan.length > 0), {
		width: W,
		height: H,
		fonts: loadFonts()
	});
	const pieces = await Promise.all(
		PAINT_ORDER.filter((slot) => slot < fan.length).map((slot) => fanPiece(fan[slot], slot))
	);
	// Rasterised by sharp's librsvg, not resvg: satori has already turned every
	// glyph into a path, so no font is needed at this step, and librsvg drew the
	// same card in ~7 ms where resvg took ~77.
	return sharp(Buffer.from(svg))
		.composite(pieces)
		.jpeg({
			// mozjpeg's tables without its trellis/scan search: measured over all
			// 887 cards, 46 MB in 10 s against full mozjpeg's 41 MB in 26 s and
			// libjpeg's 55 MB in 9 s. Every deploy pays the time; the bytes, once.
			quality: 80,
			mozjpeg: true,
			trellisQuantisation: false,
			overshootDeringing: false,
			optimiseScans: false
		})
		.toBuffer();
}

// ── Run ─────────────────────────────────────────────────────────────────────

async function main() {
	const build = resolve(process.cwd(), process.argv[2] ?? 'build');
	const started = Date.now();
	const coverFiles = covers(build);
	const failed = [];
	const pages = versePages(build);
	async function one(file) {
		const [book, chapter, verse] = relative(join(build, 'scripture'), dirname(file)).split(sep);
		const dest = join(build, verseCardUrl(book, Number(chapter), Number(verse)));
		try {
			mkdirSync(dirname(dest), { recursive: true });
			const page = verseData(readFileSync(file, 'utf8'));
			if (!page) throw new Error('no scripture data inlined in the page');
			writeFileSync(dest, await draw(page, coverFiles));
		} catch (err) {
			failed.push(`  ${book} ${chapter}:${verse} — ${err.message}`);
			// The house card, best effort: if even that cannot be written the page
			// names a missing image, which is still better than a failed deploy.
			await sharp(join(build, FALLBACK))
				.resize(W, H)
				.jpeg({ quality: 82 })
				.toFile(dest)
				.catch(() => {});
		}
	}
	// A pool of eight: satori is synchronous JS, but rasterising and the JPEG
	// encode run on libvips' own threads, so keeping eight cards in flight keeps
	// them busy — and a slow card holds up only its own worker, not a batch.
	let next = 0;
	const worker = async () => {
		while (next < pages.length) await one(pages[next++]);
	};
	await Promise.all(Array.from({ length: 8 }, worker));
	if (failed.length) {
		console.warn(
			`build-verse-cards: ${failed.length} page(s) got the default card:\n${failed.join('\n')}`
		);
	}
	console.log(
		`build-verse-cards: ${pages.length - failed.length} cards, ${failed.length} fallbacks, ` +
			`in ${((Date.now() - started) / 1000).toFixed(1)}s`
	);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
	// A share image is never worth a failed deploy: anything this misses, the
	// pages still render; they only name a card that is not there.
	await main().catch((err) => console.warn(`build-verse-cards: skipped — ${err.stack ?? err}`));
}
