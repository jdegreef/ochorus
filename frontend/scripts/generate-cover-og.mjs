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
 * objects. These are laid out here too, now — but in CSS, and in the same
 * lengths `BookCover.svelte` uses, which satori's partial flexbox could not
 * carry (container units, `text-wrap: balance`, a rule drawn from gradients).
 * Chromium runs the real thing.
 *
 * WHY THE TYPE IS DRAWN HERE AT ALL
 * It did not used to be, for the plates: the committed SVG had the words in it
 * and this script inlined the file and photographed it. That is what changed —
 * a plate is a wordless GROUND now, so a screenshot of one is a coloured
 * rectangle with an emblem on it. Both tiers therefore go through one
 * composition, which is also the first time the art twins get the brand mark
 * the site draws over them.
 *
 * The old note here explained that Georgia was remapped to Fraunces, because
 * the SVG could only name a face a device already has. There is nothing left to
 * remap: the type asks for the real families, and the same six woff2 files the
 * app loads are inlined below.
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

// Named with their extension because this is a plain .mjs script: Node resolves
// it, and nothing type-checks this file. Both modules are import-free at
// runtime for exactly this reason — see `coverStyles.ts`'s header and
// `nodeLoadable.test.ts`.
import { coverStyleFor } from '../src/lib/coverStyles.ts';
import { eraOf } from '../src/lib/eras.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = resolve(HERE, '../static');
const COVERS = resolve(STATIC, 'covers');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
const MODULES = resolve(HERE, '../node_modules');

/**
 * The cover faces, by the family name their @font-face declares, and the latin
 * woff2 the app itself loads. `app.css` maps these onto `--cover-face-*`
 * tokens; `coverStyles.ts` hands back one of those tokens, so declaring them
 * under the same names is all it takes for a card to be set in the face its
 * cover is set in.
 *
 * Latin only: a twin is the English card (see ONE PER SLUG below).
 */
const COVER_FACES = {
	'Fraunces Variable': '@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2',
	'Cinzel Variable': '@fontsource-variable/cinzel/files/cinzel-latin-wght-normal.woff2',
	'EB Garamond Variable':
		'@fontsource-variable/eb-garamond/files/eb-garamond-latin-wght-normal.woff2',
	'Playfair Display Variable':
		'@fontsource-variable/playfair-display/files/playfair-display-latin-wght-normal.woff2',
	'IM Fell English': '@fontsource/im-fell-english/files/im-fell-english-latin-400-normal.woff2',
	'Libre Baskerville':
		'@fontsource/libre-baskerville/files/libre-baskerville-latin-400-normal.woff2'
};

/** The cover's own canvas — `covers.py`'s W, H. A twin is the same picture. */
const WIDTH = 600;
const HEIGHT = 800;

// ── The content ─────────────────────────────────────────────────────────────

/** Author slug → the fields a cover needs of them, from the shared fixture. */
function authors() {
	const rows = JSON.parse(readFileSync(resolve(CONTENT, 'authors.json'), 'utf8'));
	return new Map(
		rows.map((r) => [
			r.fields.slug,
			{ slug: r.fields.slug, name: r.fields.name, birth_year: r.fields.birth_year ?? null }
		])
	);
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
	const people = authors();
	return readdirSync(resolve(CONTENT, 'books'))
		.filter((f) => f.endsWith('.en.json'))
		.sort()
		.flatMap((file) => JSON.parse(readFileSync(resolve(CONTENT, 'books', file), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map(({ fields }) => {
			const author = people.get(fields.author[0]) ?? {
				slug: fields.author[0],
				name: fields.author[0],
				birth_year: null
			};
			return {
				slug: fields.slug,
				title: fields.title,
				subtitle: fields.subtitle || '',
				author: author.name,
				// The card is set in the face the cover is set in — one table, read
				// from the app's own module rather than restated here.
				style: coverStyleFor(eraOf(author.birth_year), author.slug),
				color: fields.cover_color || '#3b5bdb',
				cover: fields.cover_url || ''
			};
		})
		.filter((b) => b.cover.endsWith('.svg') || b.cover.startsWith('/covers/art/'));
}

// ── The page ────────────────────────────────────────────────────────────────

const dataUri = (file, mime) => `data:${mime};base64,${readFileSync(file).toString('base64')}`;

/**
 * The cover faces, under the names the app declares them by.
 *
 * The plate used to name Georgia and this script mapped Georgia to Fraunces,
 * because an `<img>`-rendered SVG cannot fetch a webfont and could only ask for
 * a face the device already had. The type is HTML now and asks for the real
 * families, so there is nothing left to map: the same six faces the browser
 * loads are loaded here, and a card is set in whatever its cover is set in.
 */
const fontFaces = () =>
	Object.entries(COVER_FACES)
		.map(
			([family, file]) =>
				`@font-face{font-family:'${family}';font-style:normal;font-weight:100 900;` +
				`src:url(${dataUri(resolve(MODULES, file), 'font/woff2')}) format('woff2')}`
		)
		.join('');

const escape = (s) =>
	s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** The brand lockup, from the copy `BrandMark.svelte` itself renders. */
const LOCKUP = readFileSync(resolve(HERE, '../src/lib/brand/ochorus-lockup.svg'), 'utf8');

/**
 * What a twin is made from, as bytes — half of the manifest's subject.
 *
 * The ground plus the type drawn over it, for BOTH tiers now: a plate file has
 * no words in it either, so retitling a book or moving it to another author
 * changes the card while nothing on disk moves. (It used to be the file alone
 * for a plate, because the words were IN the file.)
 *
 * The author's STYLE is the other half of what a card is made from, and it is
 * deliberately not in here: `CoverAssetTests` recomputes this digest to prove
 * the twins were re-run, and that gate is Python — it cannot read a table in
 * `coverStyles.ts`. A digest it cannot recompute is a digest that fails the
 * build forever. So the style is recorded BESIDE this instead, and checked by
 * `coverOgManifest.test.ts`, which can read the table. Each side checks the
 * half it can actually derive.
 */
function inputs(book) {
	const ground = readFileSync(resolve(STATIC, book.cover.replace(/^\//, '')));
	return Buffer.concat([
		ground,
		Buffer.from(`\0${book.title}\0${book.subtitle}\0${book.author}`)
	]);
}

/**
 * One book's cover, as a page — the same composition for a painting and for a
 * plate, because the two tiers are the same shape: a wordless ground with the
 * book's type over it.
 *
 * THE LENGTHS ARE `cqw`, and the plate below is the container, exactly as in
 * `BookCover.svelte`. That is not a flourish: it means the numbers here are
 * that component's numbers, copied as written rather than multiplied out to
 * pixels — a 600-wide plate makes a cqw six units, and this canvas is 600 wide,
 * so a reviewer can diff the two files line for line. The composition is still
 * a COPY (there is no way to run a Svelte component in here), which is why it
 * is kept as thin as it can be and why the manifest above exists.
 */
function coverPage(book) {
	const art = book.cover.startsWith('/covers/art/');
	const groundFile = resolve(STATIC, book.cover.replace(/^\//, ''));
	// A painting is an <img> so `object-fit` can crop it; a plate is inlined,
	// which is what lets its gradient and emblem paint at any size without a
	// second file. Neither carries a word.
	const ground = art
		? `<img class="ground" src="${dataUri(groundFile, 'image/jpeg')}" alt="">`
		: `<div class="ground">${readFileSync(groundFile, 'utf8')}</div>`;
	const rule = { plain: '', double: 'rule-double', diamond: 'rule-diamond' }[book.style.rule];
	return `<style>${fontFaces()}
html,body{margin:0}
.plate{container-type:inline-size;position:relative;width:${WIDTH}px;height:${HEIGHT}px;
  overflow:hidden;color:#fff;text-align:center}
.ground{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.ground svg{display:block;width:100%;height:100%}
/* Only a painting gets a scrim: a plate's colour is floored for contrast where
   it is minted (covers.ink_safe), a photograph's brightness is nobody's to
   promise. Both numbers are BookCover's .over-art. */
.scrim{position:absolute;inset:0;background:linear-gradient(180deg,
  rgb(0 0 0 / .62) 0%, rgb(0 0 0 / .34) 30%, rgb(0 0 0 / .4) 70%, rgb(0 0 0 / .7) 100%),
  rgb(26 20 16 / .26)}
.type{position:absolute;inset:0;display:flex;flex-direction:column;
  padding:17cqw 7cqw 9cqw;box-sizing:border-box}
.type::before{content:'';position:absolute;inset:4.3cqw;
  border:1px solid rgb(255 255 255 / ${art ? '.3' : '.22'})}
.byline{font-size:3.9cqw;letter-spacing:0.28em;text-transform:uppercase;opacity:.86;
  font-family:var(--font-display);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.middle{margin:auto 0}
.title{font-family:${book.style.face};font-weight:${book.style.weight};
  font-size:calc(9.5cqw * ${book.style.scale});letter-spacing:${book.style.tracking};
  text-transform:${book.style.transform};line-height:1.15;text-wrap:balance}
.rule{width:12.7cqw;margin:5cqw auto 0;height:1px;background:rgb(255 255 255 / .55)}
.rule-double{width:16cqw;height:0.9cqw;background:
  linear-gradient(rgb(255 255 255 / .55) 0 0) top / 100% 1px no-repeat,
  linear-gradient(rgb(255 255 255 / .4) 0 0) bottom / 100% 1px no-repeat}
.rule-diamond{position:relative;width:18cqw;height:1.6cqw;background:
  linear-gradient(rgb(255 255 255 / .55) 0 0) left center / 6cqw 1px no-repeat,
  linear-gradient(rgb(255 255 255 / .55) 0 0) right center / 6cqw 1px no-repeat}
.rule-diamond::before{content:'';position:absolute;inset:50% auto auto 50%;
  width:1.1cqw;height:1.1cqw;translate:-50% -50%;rotate:45deg;
  border:1px solid rgb(255 255 255 / .62)}
.subtitle{margin-top:3cqw;font-family:var(--font-display);font-style:italic;
  font-size:3.7cqw;opacity:.85}
.emblem-band{height:20cqw;margin-bottom:4cqw}
.mark{margin:0 auto;height:13.7cqw;opacity:.82;color:#fff}
.mark svg{height:100%;width:auto;display:block}
:root{--font-display:'Fraunces Variable',Georgia,serif}
</style>
<div class="plate">
  ${ground}
  ${art ? '<div class="scrim"></div>' : ''}
  <div class="type">
    <div class="byline">${escape(book.author)}</div>
    <div class="middle">
      <div class="title">${escape(book.title)}</div>
      <div class="rule ${rule}"></div>
      ${book.subtitle ? `<div class="subtitle">${escape(book.subtitle)}</div>` : ''}
    </div>
    ${art ? '' : '<div class="emblem-band"></div>'}
    <div class="mark">${LOCKUP}</div>
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
		manifest[book.slug] = { ground: digest(inputs(book)), style: book.style.id };
		await page.setContent(coverPage(book));
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
					'GENERATED by npm run og:covers. slug -> what each twin was made from, ' +
					'so a stale twin can be told from a fresh one: `ground` digests the ' +
					'cover file and the type over it (checked by CoverAssetTests), `style` ' +
					'names the house style it was set in (checked by coverOgManifest.test.ts).',
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
