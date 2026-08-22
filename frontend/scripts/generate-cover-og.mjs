/**
 * Generate the Open Graph twin for every book cover that cannot be its own.
 *
 * Output: frontend/static/covers/<slug>.png (600x800), committed to the repo.
 * NOT part of the build or CI; run it by hand after a cover changes:
 *
 *     cd frontend && npm run og:covers
 *
 * WHY A TWIN EXISTS AT ALL
 * `books/[slug]/+page.svelte` points og:image at `/covers/<slug>.png` whenever
 * the cover cannot stand in for itself. Two tiers cannot:
 *
 *   * a generated `.svg` plate — WhatsApp, Facebook and X all refuse an SVG;
 *   * a `covers/art/` painting — one shared file with no words on it, because
 *     the title is drawn over it in the browser. Shared as-is it is a painting
 *     with no idea which book it belongs to.
 *
 * `CoverAssetTests.test_covers_that_cannot_be_shared_have_a_raster_twin` fails
 * the build when one is missing. It could not tell a STALE twin from a fresh
 * one, which is exactly what went wrong: the committed twins were a design
 * generation out of date — "OCHORUS" at the top and the author at the foot,
 * the inverted layout that `covers.py` abandoned — and every gate stayed green
 * for months while every shared link showed the old cover.
 *
 * So this also writes `og-manifest.json`: slug → a digest of the INPUTS each
 * twin was made from. `CoverAssetTests.test_every_twin_was_made_from_the_cover
 * _it_stands_in_for` recomputes those digests and fails when one has moved, so
 * redrawing a plate or retitling a book now breaks the build until this is
 * re-run. It cannot catch a change to the COMPOSITION below — nothing but
 * running it can — which is why the tiers are kept as thin as they are.
 *
 * ONE PER SLUG, ENGLISH. The fallback path is keyed by slug alone, so a
 * translated page shares the English card. That is `generate-og.mjs`'s policy,
 * inherited rather than invented here: scrapers rarely read localized cards.
 *
 * NOT EVERY TWIN IS THIS SCRIPT'S. A work whose English cover is a DESIGNED
 * raster needs a twin too — its translated editions wear generated plates, and
 * a plate arms the fallback — but that twin is a crop of the designed artwork,
 * written by `localize_covers.py`'s `ensure_og_twin` at the moment the
 * localized SVG lands. Fourteen of the 53 are its; the 37 here are the two
 * tiers it does not cover. They never collide (a work is one tier), and the
 * split is worth naming because one filename with two writers is the kind of
 * thing that grows a third.
 *
 * WHY CHROMIUM AND NOT SATORI
 * The sermon cards are satori because they are laid out here, in JSX-ish
 * objects. These are not: the plate is a committed SVG that `covers.py` already
 * drew, and re-describing its layout in a second engine is the drift this repo
 * keeps paying for (STYLE_GUIDE section 5). Chromium renders the committed file
 * itself — the artwork stays the one in `static/covers/`, and this only
 * photographs it.
 *
 * WHY THE TYPE COMES OUT IN FRAUNCES, NOT GEORGIA
 * The plate names Georgia because an SVG served through `<img>` cannot fetch a
 * webfont, so it may only name fonts the device already has. A PNG has no such
 * limit — the type is baked in — so it is set in the brand serif the site uses
 * everywhere else, which is what the SVG's stack is standing in for. The twin
 * is therefore closer to the design than the file it is made from, not further
 * from it. `Georgia` is mapped to Fraunces below rather than the SVG being
 * edited, so the committed artwork stays untouched and unconditional: the same
 * face renders on any machine, whether or not it has Georgia installed.
 *
 * PALETTISED to 256 colours, which is `ensure_og_twin`'s reasoning applied to
 * the other two tiers: at the size a share card is ever seen the difference is
 * invisible, and truecolour costs about twice the bytes — measured across all
 * 37, 16.1 MB against 8.4 MB. These are committed files, so that is repo weight
 * paid once and forever.
 *
 * Writes only the files whose BYTES changed, so adding one book touches one
 * file. Deliberate: the first sermon-card version skipped any slug that already
 * had a file, which kept the diff clean but shipped stale cards — the failure
 * this whole script exists to repair.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { chromium } from 'playwright';
import sharp from 'sharp';

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = resolve(HERE, '../static');
const COVERS = resolve(STATIC, 'covers');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
const FRAUNCES = resolve(HERE, '../node_modules/@fontsource-variable/fraunces/files');

/** The cover's own canvas — `covers.py`'s W, H. A twin is the same picture. */
const WIDTH = 600;
const HEIGHT = 800;

// ── The content ─────────────────────────────────────────────────────────────

/** Author slug → display name, from the shared authors fixture. */
function authorNames() {
	const rows = JSON.parse(readFileSync(resolve(CONTENT, 'authors.json'), 'utf8'));
	return new Map(rows.map((r) => [r.fields.slug, r.fields.name]));
}

/**
 * Every English book whose cover cannot be its own og:image, in slug order.
 *
 * The same two conditions the fixture gate tests, deliberately spelled out
 * again rather than shared: that gate is what proves this script was run, and a
 * gate importing its subject's definition of "needs one" can only ever agree
 * with it.
 */
function needTwins() {
	const names = authorNames();
	return readdirSync(resolve(CONTENT, 'books'))
		.filter((f) => f.endsWith('.en.json'))
		.sort()
		.flatMap((file) => JSON.parse(readFileSync(resolve(CONTENT, 'books', file), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map(({ fields }) => ({
			slug: fields.slug,
			title: fields.title,
			subtitle: fields.subtitle || '',
			author: names.get(fields.author[0]) ?? fields.author[0],
			color: fields.cover_color || '#3b5bdb',
			cover: fields.cover_url || ''
		}))
		.filter((b) => b.cover.endsWith('.svg') || b.cover.startsWith('/covers/art/'));
}

// ── The page ────────────────────────────────────────────────────────────────

const dataUri = (file, mime) =>
	`data:${mime};base64,${readFileSync(file).toString('base64')}`;

/**
 * Fraunces, under the name the artwork asks for.
 *
 * Both faces are the variable `wght` files the app itself loads, so the twin
 * and the site are set in the same metal. Latin only: these are English cards.
 */
const fontFaces = () =>
	['normal', 'italic']
		.map(
			(style) => `@font-face{font-family:Georgia;font-style:${style};font-weight:100 900;` +
				`src:url(${dataUri(resolve(FRAUNCES, `fraunces-latin-wght-${style}.woff2`), 'font/woff2')})` +
				` format('woff2-variations')}`
		)
		.join('');

const escape = (s) =>
	s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/**
 * What a twin is made from, as bytes — the manifest's subject.
 *
 * The plate is its SVG, whole. The painting is the artwork plus the type drawn
 * over it, so the strings are in here too: retitling a curated book changes its
 * card, and the painting on disk does not move.
 */
function inputs(book) {
	const art = book.cover.startsWith('/covers/art/');
	const file = readFileSync(
		art ? resolve(STATIC, book.cover.replace(/^\//, '')) : resolve(COVERS, `${book.slug}.svg`)
	);
	return art
		? Buffer.concat([file, Buffer.from(`\0${book.title}\0${book.subtitle}\0${book.author}`)])
		: file;
}

/**
 * A plate: the committed SVG itself, inlined so the page's fonts apply.
 *
 * Inline rather than `<img src=...>` — an `<img>` renders the SVG in an
 * isolated document that the @font-face above cannot reach, which is the whole
 * reason the plate names a system font in the first place.
 */
function platePage(slug) {
	const svg = readFileSync(resolve(COVERS, `${slug}.svg`), 'utf8');
	return `<style>${fontFaces()}html,body{margin:0}svg{display:block;width:${WIDTH}px;height:${HEIGHT}px}</style>${svg}`;
}

/**
 * A painting: the shared artwork with this book's type over it.
 *
 * The composition `BookCover` draws over `covers/art/` — the scrim, the frame,
 * the byline at the top, the title centred — because that IS the cover for
 * these ten works, and a share card showing the bare painting would be a
 * picture with no book on it. Proportions echo the plate (STYLE_GUIDE section
 * 5): same frame inset, same optical centre, same rule.
 */
function artPage({ title, subtitle, author, cover }) {
	const painting = dataUri(resolve(STATIC, cover.replace(/^\//, '')), 'image/jpeg');
	return `<style>${fontFaces()}
html,body{margin:0}
.plate{position:relative;width:${WIDTH}px;height:${HEIGHT}px;overflow:hidden;
  font-family:Georgia,serif;color:#fff;text-align:center}
.plate img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
/* A wash, not an eraser: the painting stays legible under the type. Heavier
   at the top and bottom, where the words are. */
.scrim{position:absolute;inset:0;background:
  linear-gradient(180deg,rgba(0,0,0,.62) 0%,rgba(0,0,0,.28) 34%,rgba(0,0,0,.30) 62%,rgba(0,0,0,.68) 100%)}
.frame{position:absolute;inset:26px;border:1.5px solid rgba(255,255,255,.34)}
.type{position:absolute;inset:26px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:0 52px}
.byline{position:absolute;top:60px;left:0;right:0;font-size:23px;letter-spacing:4px;
  opacity:.9;text-transform:uppercase}
.title{font-size:60px;font-weight:600;line-height:1.16;margin:0;
  text-shadow:0 2px 18px rgba(0,0,0,.45)}
.rule{width:76px;height:1.5px;background:rgba(255,255,255,.62);margin:34px 0 0}
.sub{font-size:24px;font-style:italic;opacity:.86;margin:18px 0 0;line-height:1.3}
</style>
<div class="plate">
  <img src="${painting}" alt="">
  <div class="scrim"></div>
  <div class="frame"></div>
  <div class="type">
    <div class="byline">${escape(author)}</div>
    <h1 class="title">${escape(title)}</h1>
    <div class="rule"></div>
    ${subtitle ? `<p class="sub">${escape(subtitle)}</p>` : ''}
  </div>
</div>`;
}

// ── The run ─────────────────────────────────────────────────────────────────

const digest = (buf) => createHash('sha256').update(buf).digest('hex');

async function main() {
	const books = needTwins();
	const browser = await chromium.launch();
	const page = await browser.newPage({
		viewport: { width: WIDTH, height: HEIGHT },
		deviceScaleFactor: 1
	});

	const wrote = [];
	const manifest = {};
	for (const book of books) {
		const art = book.cover.startsWith('/covers/art/');
		manifest[book.slug] = digest(inputs(book));
		await page.setContent(art ? artPage(book) : platePage(book.slug));
		// The faces are data URIs, so this resolves immediately — but a
		// screenshot taken before it does silently falls back to the default
		// serif, which is precisely the defect this script repairs.
		await page.evaluate(() => document.fonts.ready);
		// `dither` defaults to 1.0, which speckles a smooth gradient; the plates
		// are mostly one, so it is turned down rather than off — off bands the
		// gradient instead, and a band is more visible than a grain.
		const png = await sharp(await page.screenshot({ type: 'png' }))
			.png({ palette: true, colours: 256, dither: 0.4, effort: 10 })
			.toBuffer();

		const dest = resolve(COVERS, `${book.slug}.png`);
		if (existsSync(dest) && digest(readFileSync(dest)) === digest(png)) continue;
		writeFileSync(dest, png);
		wrote.push(`${book.slug}.png  ${art ? 'painting' : 'plate'}`);
	}

	await browser.close();

	// Sorted, so the file is a stable diff rather than readdir order.
	writeFileSync(
		resolve(COVERS, 'og-manifest.json'),
		JSON.stringify(
			{
				_comment:
					'GENERATED by npm run og:covers. slug -> digest of what each twin was ' +
					'made from, so the fixture gate can tell a stale twin from a fresh one.',
				twins: Object.fromEntries(Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)))
			},
			null,
			'\t'
		) + '\n'
	);

	console.log(`wrote ${wrote.length} of ${books.length} twins`);
	for (const line of wrote) console.log(`    ${line}`);
}

await main();
