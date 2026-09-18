/**
 * Compose every edition's landscape share card into the build.
 *
 * Runs as `postbuild`, so it runs on every deploy and in CI's build job:
 *
 *     npm run build          # vite build, then this
 *     node scripts/build-share-cards.mjs [outDir]   # by hand; default ./build
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
 * scaled, on a heavily blurred and dimmed field of its own colours. No fonts,
 * no browser: `sharp` alone, deterministic, about a tenth of a second a card.
 *
 * WHY AT BUILD, NOT COMMITTED
 * The other cards are hand-run and committed, and each needs a manifest and a
 * staleness gate to catch the day its source moved and nobody re-ran it. This
 * one is a pure function of files already in the repo, so it is rebuilt from
 * them on every deploy: nothing to commit (~340 cards, ~12 MB), nothing to
 * go stale, nothing to gate.
 *
 * SOURCE OF TRUTH: the committed fixtures, as for the twins. The book pages
 * are prerendered from the API, which is seeded from these same files. A
 * published edition whose source raster is missing FAILS THE BUILD — a page
 * pointing its og:image at a card that was never made is the failure this
 * refuses to ship. (`coverArt.test.ts` asserts the same thing in the unit
 * suite, so it surfaces before a build does.)
 */
import sharp from 'sharp';
import { mkdirSync, readFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
	LANDSCAPE_HEIGHT as H,
	LANDSCAPE_WIDTH as W,
	landscapeUrl,
	shareImage
} from '../src/lib/coverArt.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = resolve(HERE, '../static');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
const OUT = resolve(process.cwd(), process.argv[2] ?? 'build');

/** The cover's box on the card: full height less a margin, at 3:4. */
const PAD = 36;
const CH = H - 2 * PAD;
const CW = Math.round((CH * 3) / 4);
const RADIUS = 10;

/** Every published edition with a cover, and the raster that stands for it. */
function editions() {
	return readdirSync(resolve(CONTENT, 'books'))
		.filter((f) => f.endsWith('.json'))
		.sort()
		.flatMap((f) => JSON.parse(readFileSync(resolve(CONTENT, 'books', f), 'utf8')))
		.filter((row) => row.model === 'library.book' && row.fields.is_published !== false)
		.map(({ fields }) => ({
			slug: fields.slug,
			language: fields.language || 'en',
			cover_url: fields.cover_url || ''
		}))
		.map((book) => ({ book, source: shareImage(book) }))
		.filter(({ source }) => source !== null);
}

/**
 * The ground: the whole cover averaged down to a 6×3 field of its colours and
 * blown back up under a heavy blur. Two drafts measured what less does: a blur
 * at card size keeps the title as smudges either side of the cover, and a
 * 24×13 crop still carries the title's band as soft blocks. Squeezing the
 * whole cover (not cropping it) into a few pixels averages the title away and
 * leaves only its palette. Dimmed so the cover sits forward of it.
 */
async function ground(src) {
	const tiny = await sharp(src).resize(6, 3, { fit: 'fill' }).toBuffer();
	return sharp(tiny)
		.resize(W, H, { fit: 'fill', kernel: 'cubic' })
		.blur(48)
		.modulate({ brightness: 0.55 })
		.toBuffer();
}

/** The cover itself, scaled into its box with rounded corners. */
async function cover(src) {
	const mask = Buffer.from(
		`<svg width="${CW}" height="${CH}"><rect width="${CW}" height="${CH}" rx="${RADIUS}" fill="#fff"/></svg>`
	);
	return sharp(src)
		.resize(CW, CH, { fit: 'cover' })
		.composite([{ input: mask, blend: 'dest-in' }])
		.png()
		.toBuffer();
}

/** A soft shadow under the cover, so it reads as an object on the ground. */
const SHADOW = await sharp({
	create: { width: CW + 60, height: CH + 60, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } }
})
	.composite([
		{
			input: Buffer.from(
				`<svg width="${CW + 60}" height="${CH + 60}"><rect x="30" y="36" width="${CW}" height="${CH}" rx="${RADIUS}" fill="#000" fill-opacity=".6"/></svg>`
			)
		}
	])
	.blur(14)
	.png()
	.toBuffer();

async function card(src, dest) {
	const left = Math.round((W - CW) / 2);
	mkdirSync(dirname(dest), { recursive: true });
	await sharp(await ground(src))
		.composite([
			{ input: SHADOW, top: PAD - 30, left: left - 30 },
			{ input: await cover(src), top: PAD, left }
		])
		.jpeg({ quality: 82, mozjpeg: true })
		.toFile(dest);
}

async function main() {
	const started = Date.now();
	const all = editions();
	const missing = all.filter(({ source }) => !existsSync(resolve(STATIC, `.${source.url}`)));
	if (missing.length) {
		throw new Error(
			`build-share-cards: ${missing.length} published edition(s) name a cover that is not ` +
				`in static/, so their share card cannot be made:\n` +
				missing.map(({ book, source }) => `  ${book.language}/${book.slug} → ${source.url}`).join('\n')
		);
	}
	// A few at a time: sharp threads each image itself, and all ~340 at once
	// only queues them behind one another while holding every buffer.
	const queue = [...all];
	const worker = async () => {
		for (let job = queue.shift(); job; job = queue.shift()) {
			await card(
				resolve(STATIC, `.${job.source.url}`),
				resolve(OUT, `.${landscapeUrl(job.book.slug, job.book.language)}`)
			);
		}
	};
	await Promise.all(Array.from({ length: 4 }, worker));
	console.log(
		`build-share-cards: ${all.length} cards into ${OUT} in ${((Date.now() - started) / 1000).toFixed(1)}s`
	);
}

await main();
