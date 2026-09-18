/**
 * Compose every landscape share card the built site asks for.
 *
 * Runs as `postbuild`, so it runs on every deploy and in CI's build job:
 *
 *     npm run build          # vite build, then this
 *     node scripts/build-share-cards.mjs [buildDir]   # by hand; default ./build
 *
 * WHY A LANDSCAPE CARD
 * Facebook, X and LinkedIn crop a link preview to 1.91:1. A book's og:image
 * was its 3:4 cover (or the cover's twin), and a 3:4 image cropped to 1.91:1
 * loses its top and bottom — where a cover keeps its byline and its title. So
 * the card a preview shows is the whole cover, set on a ground as wide as the
 * crop.
 *
 * WHY IT IS COMPOSED, NOT DRAWN
 * Every other share card is drawn: satori for the sermon and topic cards,
 * Chromium for the cover twins. This one draws nothing. The cover it shows
 * already carries its title in its pixels — a designed cover by design, every
 * other edition through its twin — shaped for its own script, Arabic and
 * Devanagari included, which satori cannot do. So a card is only that raster,
 * scaled, on a blurred and dimmed field of its own colours. No fonts, no
 * browser: `sharp` alone, deterministic, a few seconds for the whole library.
 *
 * WHY AT BUILD, NOT COMMITTED
 * The other cards are hand-run and committed, and each needs a manifest and a
 * staleness gate to catch the day its source moved and nobody re-ran it. This
 * one is a pure function of files the build already holds, so it is rebuilt
 * with them: nothing to commit (~340 cards, ~12 MB), nothing to go stale.
 *
 * THE BUILD IS THE SOURCE OF TRUTH — not the fixtures. The pages are
 * prerendered from the live API, and a published edition can exist there
 * without a fixture row (the admin can add one; `seed_books` never deletes).
 * Enumerated from the fixtures, such a page would name a card that was never
 * made, and its path would be answered with the SPA's HTML fallback. So this
 * reads the prerendered pages themselves: each og:image under `/og/covers/`
 * is a card to make, and the book page's `Book.image` (the cover, from
 * `shareImage`) is what to make it from. A card whose source cannot be found
 * gets the site's default card instead, and says so: a link preview with the
 * house card beats one with none, and one edition missing a cover must not
 * fail a deploy. (`coverArt.test.ts` holds the committed library to having
 * every source, so the fallback is for rows the repo does not know about.)
 */
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { LANDSCAPE_HEIGHT as H, LANDSCAPE_WIDTH as W } from '../src/lib/coverArt.ts';

const BUILD = resolve(process.cwd(), process.argv[2] ?? 'build');
const CARDS = '/og/covers/';
const FALLBACK = '/og/default.png';

/** The cover's height on the card: the full height less a margin. Its width
 *  follows its own aspect — see `cover()`. */
const PAD = 36;
const CH = H - 2 * PAD;
const RADIUS = 10;
/** How far the shadow spreads past the cover on each side. */
const SPREAD = 30;

// ── What the site asks for ──────────────────────────────────────────────────

/** Every prerendered page under the directories that name a cover card. */
function pages(dir = BUILD) {
	return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
		const path = join(dir, e.name);
		if (e.isDirectory()) return pages(path);
		return e.name === 'index.html' && /\/(books|authors)\//.test(path) ? [path] : [];
	});
}

const OG_IMAGE = /<meta property="og:image" content="([^"]+)"/;
const LD = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;

/** Card path → the cover to compose it from (null where no page says). */
function wanted() {
	const cards = new Map();
	for (const file of pages()) {
		const html = readFileSync(file, 'utf8');
		const og = OG_IMAGE.exec(html)?.[1];
		if (!og) continue;
		const card = new URL(og).pathname;
		if (!card.startsWith(CARDS)) continue;
		if (!cards.has(card)) cards.set(card, null);
		// Only a book page states the cover; an author page names the same card
		// as its first book's page and leaves the source to that page.
		for (const [, json] of html.matchAll(LD)) {
			const ld = JSON.parse(json);
			if (ld['@type'] === 'Book' && ld.image) cards.set(card, new URL(ld.image).pathname);
		}
	}
	return cards;
}

// ── The card ────────────────────────────────────────────────────────────────

/**
 * The ground: the whole cover averaged down to a 6×3 field of its colours and
 * blown back up. Squeezing the cover (not cropping it) averages its title
 * away and leaves only its palette; two drafts showed that less leaves the
 * title as smudges either side of the cover. Blurred at a tenth of the card's
 * size — at full size the blur was ~70% of the script's time, for a result
 * that differed from this by under half a level per pixel.
 */
async function ground(src) {
	const tiny = await sharp(src).resize(6, 3, { fit: 'fill' }).toBuffer();
	const small = await sharp(tiny)
		.resize(W / 10, Math.round(H / 10), { fit: 'fill', kernel: 'cubic' })
		.blur(4.8)
		.modulate({ brightness: 0.55 })
		.toBuffer();
	return sharp(small).resize(W, H, { fit: 'fill', kernel: 'cubic' }).toBuffer();
}

/**
 * The cover itself, at the card's height and ITS OWN aspect, with rounded
 * corners. Never cropped to 3:4: a designed cover carries its byline, frame
 * and mark in its pixels at the edges, and seven of them are ~0.66, so a 3:4
 * crop cut ~6% off each end — the Inner Chamber lost the top of its frame into
 * its byline. `BookCover` mats these covers for the same reason.
 */
async function cover(src) {
	const { width = 3, height = 4 } = await sharp(src).metadata();
	const cw = Math.min(Math.round((CH * width) / height), W - 2 * PAD);
	const mask = `<svg width="${cw}" height="${CH}"><rect width="${cw}" height="${CH}" rx="${RADIUS}" fill="#fff"/></svg>`;
	const image = await sharp(src)
		.resize(cw, CH, { fit: 'fill' })
		.composite([{ input: Buffer.from(mask), blend: 'dest-in' }])
		.png()
		.toBuffer();
	return { image, cw };
}

/** A soft shadow under a cover of this width, so it reads as an object on the
 *  ground. Covers come in a handful of widths, so each is drawn once. */
const shadows = new Map();
function shadow(cw) {
	if (!shadows.has(cw)) {
		const svg = `<svg width="${cw + 2 * SPREAD}" height="${CH + 2 * SPREAD}"><rect x="${SPREAD}" y="${SPREAD + 6}" width="${cw}" height="${CH}" rx="${RADIUS}" fill="#000" fill-opacity=".6"/></svg>`;
		shadows.set(cw, sharp(Buffer.from(svg)).blur(14).png().toBuffer());
	}
	return shadows.get(cw);
}

async function card(src, dest) {
	const { image, cw } = await cover(src);
	const left = Math.round((W - cw) / 2);
	mkdirSync(dirname(dest), { recursive: true });
	await sharp(await ground(src))
		.composite([
			{ input: await shadow(cw), top: PAD - SPREAD, left: left - SPREAD },
			{ input: image, top: PAD, left }
		])
		.jpeg({ quality: 82, mozjpeg: true })
		.toFile(dest);
}

/** The house card, for a page whose cover the build does not hold. */
async function fallback(dest) {
	mkdirSync(dirname(dest), { recursive: true });
	await sharp(join(BUILD, FALLBACK)).resize(W, H).jpeg({ quality: 82 }).toFile(dest);
}

async function main() {
	const started = Date.now();
	const jobs = [...wanted()].map(([card, source]) => {
		const src = source && join(BUILD, source);
		return { card, src: src && existsSync(src) ? src : null, source };
	});
	const orphans = jobs.filter((j) => !j.src);
	if (orphans.length) {
		console.warn(
			`build-share-cards: ${orphans.length} card(s) have no cover in the build, so they get ` +
				`the default card:\n` +
				orphans.map((j) => `  ${j.card} ← ${j.source ?? 'no Book.image on any page'}`).join('\n')
		);
	}
	// A few at a time: sharp threads each image itself, and all at once only
	// queues them behind one another while holding every buffer.
	for (let i = 0; i < jobs.length; i += 4) {
		await Promise.all(
			jobs.slice(i, i + 4).map((j) =>
				j.src ? card(j.src, join(BUILD, j.card)) : fallback(join(BUILD, j.card))
			)
		);
	}
	console.log(
		`build-share-cards: ${jobs.length - orphans.length} cards, ${orphans.length} fallbacks, ` +
			`in ${((Date.now() - started) / 1000).toFixed(1)}s`
	);
}

await main();
