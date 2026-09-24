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
 * THE MANIFEST IS ALSO READ, which it was not for a long time. It was written
 * every run and consulted only by a test, while this script launched Chromium
 * and re-rendered all 134 cards each time, then discarded the ones whose bytes
 * matched. Comparing the digests it wrote last time first takes a run from
 * minutes to about two seconds. A card is skipped only when its `ground` and
 * `style` are unchanged AND the global `css` and `markup` digests still match
 * AND the file is still on disk; `--force` ignores all of that.
 *
 * That also stopped a quieter problem. These PNGs are reproducible on one
 * machine and NOT across machines — a different Chromium or libvips build
 * re-encodes the same pixels a shade differently, and twelve twins drawn in
 * another session came back as twelve modified files here for a mean-brightness
 * difference of 0.3. Because a skip does not re-encode, a checkout whose inputs
 * have not moved no longer churns files just for having been run somewhere else.
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
import {
	existsSync,
	mkdirSync,
	readFileSync,
	readdirSync,
	statSync,
	writeFileSync
} from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { chromium } from 'playwright';
import sharp from 'sharp';

// Named with their extension because this is a plain .mjs script: Node resolves
// it, and nothing type-checks this file. Both modules are import-free at
// runtime for exactly this reason — see `coverStyles.ts`'s header and
// `nodeLoadable.test.ts`.
import {
	TWIN_HEIGHT,
	TWIN_WIDTH,
	hasTwin,
	isArtCover,
	twinUrl
} from '../src/lib/coverArt.ts';
// The cover's type, as markup — the same tree `BookCover` renders, stated once
// so `coverMarkupParity.test.ts` can hold the two renderers against each other.
// It used to be hand-built below, and had drifted into a card with no
// `script-` class, no `lang` and no `dir`: an Arabic preview would have been
// set in the Latin face and laid out left-to-right.
import { coverPlateMarkup } from '../src/lib/coverCardMarkup.ts';
import { coverTitle } from '../src/lib/coverTitle.ts';
import { scrimStrength } from '../src/lib/coverScrim.ts';
import { coverLayoutFor, layoutKey, typeTopFor } from '../src/lib/coverLayouts.ts';
import { groundBar } from '../src/lib/groundBars.ts';
import { coverStyleFor, scriptOf, volumeNumeral } from '../src/lib/coverStyles.ts';
import { eraOf } from '../src/lib/eras.ts';
import { baseEdition } from '../src/lib/reading-schema.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = resolve(HERE, '../static');
const COVERS = resolve(STATIC, 'covers');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
const MODULES = resolve(HERE, '../node_modules');
const APP_CSS = readFileSync(resolve(HERE, '../src/app.css'), 'utf8');
// Stripped of comments ONCE, here, rather than inlined whole into every card.
// `cover-type.css` is deliberately more than half prose — it is where the two
// renderers' shared reasoning lives — and that prose is ~24 KB that Chromium
// would otherwise parse again for each of the sixty-odd books in a full run.
// It is also exactly the text the manifest digest below already ignores, so
// stripping it changes nothing about what is drawn or when a card is redrawn.
const COVER_CSS = readFileSync(
	resolve(HERE, '../src/lib/components/cover-type.css'),
	'utf8'
).replace(/\/\*[\s\S]*?\*\//g, '');

/** The cover's own canvas — `covers.py`'s W, H. A twin is the same picture,
 *  and its size is the app's, so the og:image dimensions a page advertises are
 *  the ones drawn here. */
const WIDTH = TWIN_WIDTH;
const HEIGHT = TWIN_HEIGHT;

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
 * Every EDITION whose cover cannot be its own og:image, in slug order.
 *
 * Every edition, not every English book, and that was the bug. A twin carries
 * the book's TITLE baked into its pixels, and `og:image` resolved to
 * `/covers/<slug>.png` — keyed by slug alone. So sharing the Arabic, Hindi or
 * Portuguese page of a book posted a preview card with the ENGLISH title on it,
 * for all 93 translated editions. Localized pages are prerendered, so that was
 * in the HTML a crawler reads, not something the runtime could correct.
 *
 * It also quietly broke the rule the content model is built on: a language with
 * no row simply does not show that item. The share layer was substituting
 * English instead of declining, which is the one fallback this library does not
 * have.
 *
 * The same two conditions the fixture gate tests, deliberately spelled out
 * again rather than shared: that gate is what proves this script was run, and a
 * gate importing its subject's definition of "needs one" can only ever agree
 * with it.
 */
function needTwins() {
	const people = authors();
	return readdirSync(resolve(CONTENT, 'books'))
		.filter((f) => f.endsWith('.json'))
		.sort()
		.flatMap((file) => JSON.parse(readFileSync(resolve(CONTENT, 'books', file), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map(({ fields }) => {
			const author = people.get(fields.author[0]) ?? {
				slug: fields.author[0],
				name: fields.author[0],
				birth_year: null
			};
			const cover = fields.cover_url || '';
			const script = scriptOf(fields.language || 'en');
			return {
				slug: fields.slug,
				// The title the cover SETS, as the component chooses it — and so the
				// one the manifest digests, which `tests_fixture` recomputes.
				title: coverTitle(fields),
				subtitle: fields.subtitle || '',
				author: author.name,
				// The card is set in the style the cover is set in — one table, read
				// from the app's own module rather than restated here.
				style: coverStyleFor(eraOf(author.birth_year), author.slug, fields.slug),
				// Its series numeral, in the edition's digits — the same call the
				// component makes, so a card and a page cannot number a book apart.
				volume: volumeNumeral(fields.series_position, baseEdition(fields.language || 'en')),
				cover,
				// The edition's language, and the script its type is set in — both
				// through the app's own table. Only English books get a twin today,
				// so these are `en`/null for every card this script currently draws;
				// they are read rather than hardcoded so that the day a translated
				// edition gets one, it is set in its own face rather than silently
				// in Latin.
				language: fields.language || 'en',
				script,
				// Where this edition's card lives, and what names it in the manifest.
				// English keeps the historic root path so cards already shared do not
				// 404; every other language sits under its own directory. The same
				// layout `covers.cover_path` gives a plate, for the same reason.
				twin: twinPath(fields.slug, fields.language || 'en'),
				// Which tier, through the app's own predicates rather than a fourth
				// hand-written copy of "what is a painting".
				art: isArtCover(cover),
				// And how far its scrim is scaled — the same table the component
				// reads. A card drawn without this wears the strength the palest
				// painting in the library needs.
				scrim: scrimStrength(fields.slug),
				// A painting's composition; a plate takes none.
				layout: isArtCover(cover) ? coverLayoutFor(author.slug, script, fields.slug) : null
			};
		})
		// How far a laid-out painting is cropped past its scan border — the
		// component asks only for a layout, so this does too.
		.map((b) => ({ ...b, bar: b.layout ? groundBar(b.cover) : 0 }))
		// Framed type set from the top (the Key Teachings) — the component's call.
		.map((b) => ({ ...b, top: b.art && typeTopFor(b.slug, b.layout) }))
		.filter((b) => hasTwin(b.cover));
}

/** (key, file) for one edition's twin, from the URL the app resolves — so the
 *  writer and the reader cannot disagree about where a card lives. */
function twinPath(slug, language) {
	const file = twinUrl(slug, language).replace('/covers/', '');
	return { key: file.replace(/\.png$/, ''), file };
}

// ── The page ────────────────────────────────────────────────────────────────

const dataUri = (file, mime) => `data:${mime};base64,${readFileSync(file).toString('base64')}`;

/**
 * The app's font wiring, read out of `app.css` rather than restated.
 *
 * Every face the covers use is fetched by an `@import '@fontsource…'` there and
 * named by a `--cover-face-*` token beside it. This takes both: it walks the
 * imports, pulls each package's own `@font-face` for the latin subset, inlines
 * the woff2 as a data URI (Chromium here has no node_modules to resolve a
 * relative `url()` against), and re-emits the token block verbatim.
 *
 * DERIVED, NOT COPIED, because the copy is what went wrong. This script used to
 * hand-map the faces AND declare only `--font-display` — so `.title`'s
 * `font-family: var(--cover-face-revival)` resolved to nothing and all 37
 * committed twins shipped set in Times, silently, while both test suites stayed
 * green. Adding a sixth cover face is now one edit in `app.css`, not four.
 *
 * PER SCRIPT, and that is the correction that matters. This inlined the latin
 * subset of the FIRST family in each token and nothing else, on the stated
 * grounds that "a twin is an English card" — true when it was written, false
 * the moment translated editions got cards of their own. The effect was not a
 * missing file but a silent substitution: `Amiri` appeared in the token block,
 * so the stack named it, while no `@font-face` for it ever reached the page.
 * Measured on the real card before this change, an Arabic title resolved to
 * Liberation Serif and Unifont — the runner's system fallbacks — where the page
 * it stands in for resolves to Amiri.
 *
 * So the families are every quoted name in the tokens, and the subsets are
 * latin, latin-ext and the CARD'S OWN script. An English card still pays for
 * latin alone; an Arabic one adds Arabic and nothing else. Italic is dropped
 * throughout — only the title takes a cover face, and it is never italic.
 */
function buildFontCss(script) {
	// The token block first: it is also the list of families a cover can ask
	// for, which is how the reader's OpenDyslexic and the UI's Hanken are left
	// out without naming either of them here.
	const tokens = [...APP_CSS.matchAll(/^\s*(--(?:cover-face-[a-z]+|font-display):[^;]+);/gm)].map(
		([, decl]) => decl.trim()
	);
	// EVERY quoted name in the tokens, because a stack's script faces sit after
	// its first: `--font-display` names Fraunces, then Amiri, then Tiro, then PT
	// Serif. Taking only the first is what left every non-Latin card unserved.
	const wanted = new Set(
		tokens.flatMap((decl) => [...decl.matchAll(/'([^']+)'/g)].map(([, f]) => f))
	);
	// The RECIPE face — still the first name in each token — is the one whose
	// absence means a cover renders in the fallback and looks deliberate, so it
	// stays the thing the completeness check below insists on. The rest of a
	// stack is script faces (checked separately, against the script actually
	// being drawn) and device families like 'Times New Roman', which ship no
	// package and would make that check throw on every run.
	const recipeFaces = new Set(
		tokens.map((decl) => /'([^']+)'/.exec(decl)?.[1]).filter((f) => f !== undefined)
	);
	// latin always — even an Arabic card sets its byline in it — plus the card's
	// own. Cyrillic takes its ext too: PT Serif splits Ukrainian's ґ out of the
	// base block, the same split that hid the gap in `--font-sans`.
	const subsets = ['latin', 'latin-ext'];
	if (script === 'arabic') subsets.push('arabic');
	if (script === 'devanagari') subsets.push('devanagari');
	if (script === 'cyrillic') subsets.push('cyrillic', 'cyrillic-ext');
	const wantedSubset = new RegExp(`url\\(\\./files/[^)]*-(${subsets.join('|')})-`);
	// Recorded HERE, while the filenames are still filenames. The blocks are
	// rewritten below to carry the woff2 inline, which is what a data URI is for
	// — and that erases the only evidence of which subset a block was. Asking
	// afterwards is asking the wrong text: it looks like no script face arrived,
	// on a run where all of them did.
	const subsetsSeen = new Set();

	const faces = [...APP_CSS.matchAll(/@import '(@fontsource[^']+)'/g)].flatMap(([, spec]) => {
		// A bare package specifier ('@fontsource-variable/fraunces') is its
		// index.css through package exports; `resolve` only gives the directory.
		let file = resolve(MODULES, spec);
		if (statSync(file).isDirectory()) file = resolve(file, 'index.css');
		const dir = dirname(file);
		return readFileSync(file, 'utf8')
			.split('@font-face')
			.slice(1)
			.map((block) => `@font-face${block.slice(0, block.indexOf('}') + 1)}`)
			// One block per subset, per style: the card's subsets, upright only,
			// and only a family some cover can name.
			.filter((block) => {
				const hit = wantedSubset.exec(block);
				if (hit) subsetsSeen.add(hit[1]);
				return hit !== null;
			})
			.filter((block) => !/font-style:\s*italic/.test(block))
			.filter((block) => wanted.has(/font-family:\s*'([^']+)'/.exec(block)?.[1] ?? ''))
			.map((block) =>
				block
					// woff2 only, and inlined: Chromium is rendering a string here,
					// with no directory for a relative url() to resolve against.
					.replace(/,\s*url\(\.\/files\/[^)]+\)\s*format\('woff'\)/g, '')
					.replace(
						/url\(\.\/files\/([^)]+)\)/g,
						(_m, name) => `url(${dataUri(resolve(dir, 'files', name), 'font/woff2')})`
					)
			);
	});

	// Compared as SETS, not counts: a family ships one block per subset, so
	// counting blocks let a missing family hide behind another family's second
	// subset — which is how a guard meant to catch exactly this defect sat green
	// while every twin rendered in the fallback face.
	const found = new Set(
		faces.map((block) => /font-family:\s*'([^']+)'/.exec(block)?.[1]).filter((f) => f)
	);
	const missing = [...recipeFaces].filter((family) => !found.has(family));
	if (missing.length) {
		throw new Error(
			`app.css names ${missing.join(', ')} in a --cover-face-* token but nothing ` +
				`@imports the package — every card wearing that recipe would render in the ` +
				`fallback face, and look deliberate.`
		);
	}
	// AND THE SCRIPT ACTUALLY HAS A FACE. The check above asks whether each
	// recipe's own family arrived; it cannot notice that an Arabic card carries
	// six Latin faces and nothing that can draw an Arabic glyph, which is
	// precisely what shipped. This asks the question the card is about.
	if (script && !subsetsSeen.has(script)) {
		throw new Error(
			`no @font-face for ${script} reached the card — every ${script} twin would ` +
				`render in whatever font the machine drawing it happens to have, and look ` +
				`deliberate. Check that a --cover-face-* or --font-display token names a ` +
				`family with a ${script} subset, and that app.css @imports it.`
		);
	}
	return `${faces.join('')}:root{${tokens.join(';')}}`;
}

/** Built once PER SCRIPT, and only when a page is actually drawn: it was a
 *  per-book call (37 x 6 file reads), and `coverOgManifest.test.ts` imports
 *  this module for `needTwins` alone and should not pay for it at all. Keyed by
 *  script because the faces a card needs depend on it — four entries at most,
 *  and the library draws its cards in slug order, so the cache still holds. */
const FONT_CSS = new Map();

/** What a card with no script of its own is set in. Said once, because the
 *  manifest records this normalised value and it has to be the same rule the
 *  faces are chosen by rather than a second copy of it. */
const scriptKey = (script) => script ?? 'latin';

/** The face block for one card's script, cut once and kept. The ONE place that
 *  populates the Map — it had become two, the page builder and the digest, and
 *  that is a quiet way for the digest to describe faces other than the ones
 *  actually rendered. */
function fontCssFor(script) {
	const key = scriptKey(script);
	if (!FONT_CSS.has(key)) FONT_CSS.set(key, buildFontCss(script));
	return FONT_CSS.get(key);
}

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
function inputs(book, ground) {
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
 * NEITHER THE COMPOSITION NOR THE MARKUP IS WRITTEN HERE. `cover-type.css` is
 * inlined whole, so this renders the rules `BookCover` renders rather than a
 * copy of them — it used to be a copy, and the copy is what shipped 37 twins
 * set in Times. The TREE was still a copy after that, and drifted the same way:
 * no `script-` class, no `lang`, no `dir`, so the first translated card would
 * have been set in the Latin face and laid out left-to-right. It now comes from
 * `coverCardMarkup.ts`, which `coverMarkupParity.test.ts` renders the component
 * against. There is still no way to mount Svelte in here — there is just no
 * longer anything left in here to keep in step by hand.
 */
function coverPage(book, groundBytes) {
	// A painting is an <img> so `object-fit` can crop it — typed by its file,
	// since the `key-teachings-*` grounds under `covers/art/` are drawn SVGs, and
	// one labelled a JPEG rendered as a broken image under the type. A plate is
	// inlined, which is what lets its gradient and emblem paint at any size
	// without a second file. Neither carries a word.
	const ground = book.art
		? `<img class="ground cover-ground"${book.bar ? ` style="--ground-bar: ${book.bar}"` : ''} src="data:${book.cover.endsWith('.svg') ? 'image/svg+xml' : 'image/jpeg'};base64,${groundBytes.toString('base64')}" alt="">`
		: `<div class="ground">${groundBytes.toString('utf8')}</div>`;
	return `<style>${fontCssFor(book.script)}${COVER_CSS}
html,body{margin:0}
/* The three things a page needs that a cover inside the app gets from its
   surroundings: the card's box, the ground's own placement, and the container
   the cq units are measured against. */
.card{position:relative;width:${WIDTH}px;height:${HEIGHT}px;overflow:hidden}
.ground{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.ground svg{display:block;width:100%;height:100%}
.cover-type{box-sizing:border-box}
.brandmark svg{height:var(--h);width:auto;display:block;margin:0 auto}
</style>
<div class="card">
  ${ground}
  ${coverPlateMarkup(
		{
			author: book.author,
			title: book.title,
			subtitle: book.subtitle,
			style: book.style,
			volume: book.volume,
			script: book.script,
			lang: book.language,
			art: book.art,
			scrim: book.scrim,
			layout: book.layout,
			top: book.top
		},
		LOCKUP
	)}
</div>`;
}

/**
 * Refuse to photograph a card whose title did not get the face it asked for.
 *
 * This is the guard the whole file was missing. `.title` names a token
 * (`var(--cover-face-revival)`); a token that is never declared makes the
 * declaration invalid, CSS falls back to the inherited family, and Chromium
 * cheerfully renders — so the script wrote 37 perfectly good PNGs set in Times
 * and reported success. Nothing downstream could tell: the digest covers the
 * INPUTS, and a PNG has no font metadata to check.
 *
 * So the browser is asked what it actually resolved. `getComputedStyle` is the
 * whole check: an undeclared token makes the declaration invalid, so the family
 * falls back to the inherited one, and that is visible here.
 *
 * TWO THINGS IT CANNOT SEE, stated so the next person does not over-trust it.
 * `document.fonts.check` is not used, because it is handed a stack ending in a
 * generic family and therefore always answers true — a declared token whose
 * woff2 failed to load would pass. `buildFontCss` covers that case instead, by
 * refusing to build when a named family has no @font-face at all. And the house
 * recipe is Fraunces, which is also the fallback, so it is the one style this
 * cannot tell from failure — and the one where failure does not matter.
 */
async function assertTitleFace(page, book) {
	const family = await page.evaluate(() => {
		const el = document.querySelector('.title');
		return el ? getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '') : '';
	});
	if (book.style !== 'house' && /^(Times|serif|)$/i.test(family)) {
		throw new Error(
			`${book.slug}: the title resolved to "${family}" — the ${book.style} face did ` +
				`not load. Check that app.css still @imports it and declares its ` +
				`--cover-face-* token; a card set in the wrong face renders without complaint.`
		);
	}
}

// ── The run ─────────────────────────────────────────────────────────────────

const digest = (buf) => createHash('sha256').update(buf).digest('hex');

/**
 * What the last run recorded, or nothing.
 *
 * The manifest has always been WRITTEN and never READ. Its own header says it
 * exists "so a stale twin can be told from a fresh one" — and the only reader
 * was a test. Meanwhile this script launched Chromium and re-rendered all 134
 * cards on every run, then threw away the ones whose bytes matched. Reading
 * back what it just wrote last time turns a multi-minute run into a few
 * seconds, using digests the gates already trust.
 */
/**
 * Everything one card is made from, as the manifest records it.
 *
 * `ground` and `style` are the two the GATES read, and their names are fixed by
 * those readers: `CoverAssetTests` recomputes `ground` in Python, and
 * `coverOgManifest.test.ts` checks `style` against the table. The rest are here
 * for the skip, and each is a way a card changes while the ground bytes and the
 * strings sit still — which, with the skip in place, means silently:
 *
 *   `scrim`  — how far the wash over a painting is scaled, per slug. NOT
 *              hypothetical, and measured on this very script: re-measuring took
 *              `prayer-the-pulse-of-life` from 0.30 to 0.90, and moving
 *              `godliness` alone redrew nothing at all — its seven translated
 *              cards kept the old wash with every gate green.
 *   `script` — which face the title is set in. Derived from the language, so it
 *              moves only if that table does; a twin whose LANGUAGE changed is a
 *              different key rather than a changed entry.
 *   `art`    — painting or plate, which is a different ground element entirely.
 *   `layout` — the composition a painting is set in (`coverLayouts.ts`), as
 *              `framed` or `<layout>/<hue>`. Checked by `coverOgManifest.test.ts`
 *              against the table, as `style` is.
 *   `bar`    — how far a laid-out painting is cropped past its scan border
 *              (`groundBars.ts`); 0 for a framed one.
 *   `volume` — the series numeral over the title. Written as null outside a
 *              series rather than left out, because the skip is lenient about
 *              an ABSENT field: a book that joined a series would otherwise
 *              find no recorded value to disagree with, and keep its old card.
 *
 * Add a field to `coverPage`'s call and it belongs here too, or the first card
 * that needs it will be skipped.
 */
function made(book, groundBytes) {
	return {
		ground: digest(inputs(book, groundBytes)),
		style: book.style,
		volume: book.volume,
		script: scriptKey(book.script),
		art: book.art,
		scrim: book.scrim,
		layout: layoutKey(book.layout, book.top),
		bar: book.bar
	};
}

/**
 * The font faces every card is drawn with, as bytes.
 *
 * Built for each script UP FRONT rather than lazily as pages are rendered, and
 * the skip is what forces that: populate the Map on demand and its contents
 * depend on which cards happened to be redrawn, so the digest would move from
 * run to run for no reason at all.
 *
 * Worth digesting because a fontsource upgrade re-cuts the woff2 and every title
 * is then set in glyphs nothing else here can see — not `ground` (the cover file
 * and the strings), not `css` (the composition), not `markup` (the tree). While
 * every twin was redrawn every run the byte comparison caught that by accident;
 * a skip that trusts the manifest needs it recorded on purpose.
 *
 * No gate recomputes this one and none should: a digest a gate cannot derive is
 * a gate that fails forever, and these come out of node_modules. It is the
 * script comparing its own arithmetic across two runs, so it cannot go
 * stale-and-unverifiable the way a gate-side digest could.
 */
function fontDigest(books) {
	for (const book of books) fontCssFor(book.script);
	const blocks = [...FONT_CSS.entries()]
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([key, css]) => `${key}\0${css}`);
	return digest(Buffer.from(blocks.join('\0')));
}

/**
 * Was this card drawn from what it is made from now?
 *
 * Strict about `ground` and `style`, which every entry has carried since the
 * manifest existed. LENIENT about a field the recorded entry simply lacks, and
 * that is a migration decision rather than laziness: add a field and every
 * committed entry is missing it, so the strict reading is "unknown, therefore
 * stale" and redraws all 134 on the next run — which on a machine whose
 * Chromium differs is a 134-file diff, the thing this skip exists to prevent,
 * reintroduced once per field added. The lenient reading backfills from what is
 * on disk, and every run after that is strict about it.
 *
 * What it costs: a card already wrong in the NEW field's dimension stays wrong,
 * because nothing recorded an old value to disagree with. So when you add one,
 * satisfy yourself the committed twins are right for it — or run `--force` once,
 * deliberately, and commit the redraw.
 */
function drawnFrom(cached, entry) {
	if (!cached || cached.ground !== entry.ground || cached.style !== entry.style) return false;
	// Not lenient about `layout`: every twin drawn before layouts existed WAS
	// framed, so an absent value is a known one, and a work newly given a layout
	// must not be skipped for lack of an old value to disagree with.
	if ((cached.layout ?? 'framed') !== entry.layout) return false;
	return Object.keys(entry).every((k) => cached[k] === undefined || cached[k] === entry[k]);
}

function lastRun() {
	const path = resolve(COVERS, 'og-manifest.json');
	if (!existsSync(path)) return null;
	try {
		return JSON.parse(readFileSync(path, 'utf8'));
	} catch {
		// A half-written or hand-mangled manifest means "redraw everything",
		// which is the safe answer and the behaviour this had before.
		return null;
	}
}

async function main() {
	const books = needTwins();
	const force = process.argv.includes('--force');
	const previous = force ? null : lastRun();
	// THE COMPOSITION IS GLOBAL, so it gates the whole skip rather than any one
	// card: a changed stylesheet or a changed markup module redraws all of them.
	// Checked once, here, because getting it wrong is not a slow run — it is 134
	// cards silently keeping a retired design, the exact failure this script was
	// written to end.
	const shared = {
		css: digest(Buffer.from(COVER_CSS)),
		markup: digest(readFileSync(resolve(HERE, '../src/lib/coverCardMarkup.ts'))),
		// THE FACES too, for the reason `fontDigest` gives. Lenient about its
		// ABSENCE, and only its absence: it arrived after the committed manifest
		// was written, and reading a missing digest as a mismatch would redraw the
		// whole library once, on the first run after it shipped. `css` and
		// `markup` stay strict — every manifest has carried both.
		fonts: fontDigest(books)
	};
	const composed =
		previous?.css === shared.css &&
		previous?.markup === shared.markup &&
		(previous.fonts === undefined || previous.fonts === shared.fonts);
	const known = composed ? (previous.twins ?? {}) : {};

	// Launched on first use, not here: a run with nothing to redraw should not
	// need a browser at all, and on a machine where Playwright's download never
	// happened that is the difference between a no-op and a crash.
	let browser = null;
	let page = null;

	const wrote = [];
	const manifest = {};
	let skipped = 0;
	for (const book of books) {
		// Read once, for the digest and for the page.
		const groundBytes = readFileSync(resolve(STATIC, book.cover.replace(/^\//, '')));
		const entry = made(book, groundBytes);
		manifest[book.twin.key] = entry;
		const dest = resolve(COVERS, book.twin.file);
		// Same inputs, same composition, and the file is still there: nothing a
		// render could produce differs from what is on disk. The file check is
		// not belt-and-braces — a twin deleted by hand leaves the manifest
		// claiming it, and skipping on the digest alone would never write it back.
		if (drawnFrom(known[book.twin.key], entry) && existsSync(dest)) {
			skipped++;
			continue;
		}

		browser ??= await chromium.launch();
		page ??= await browser.newPage({
			viewport: { width: WIDTH, height: HEIGHT },
			deviceScaleFactor: 1
		});
		await page.setContent(coverPage(book, groundBytes));
		// The faces are data URIs, so this resolves immediately — but a
		// screenshot taken before it does silently falls back to the default
		// serif, which is precisely the defect this script repairs.
		await page.evaluate(() => document.fonts.ready);
		await assertTitleFace(page, book);
		// `dither` defaults to 1.0, which speckles a smooth gradient; the plates
		// are mostly one, so it is turned down rather than off — off bands the
		// gradient instead, and a band is more visible than a grain.
		const png = await sharp(await page.screenshot({ type: 'png' }))
			.png({ palette: true, colours: 256, dither: 0.4, effort: 10 })
			.toBuffer();

		if (existsSync(dest) && digest(readFileSync(dest)) === digest(png)) continue;
		// A translated edition's card is the first thing written into its language
		// directory when that language has no plate of its own.
		mkdirSync(dirname(dest), { recursive: true });
		writeFileSync(dest, png);
		wrote.push(`${book.twin.file}  ${book.art ? 'painting' : 'plate'}  ${book.style}`);
	}

	await browser?.close();

	// Sorted, so the file is a stable diff rather than readdir order.
	writeFileSync(
		resolve(COVERS, 'og-manifest.json'),
		JSON.stringify(
			{
				_comment:
					'GENERATED by npm run og:covers. slug -> what each twin was made from, ' +
					'so a stale twin can be told from a fresh one: `ground` digests the ' +
					'cover file and the type over it (checked by CoverAssetTests), `style` ' +
					'names the house style it was set in, and `css` digests the composition ' +
					'they were drawn with (both checked by coverOgManifest.test.ts). ' +
					'`script`, `art`, `scrim`, `layout` and `fonts` are the rest of what a card is ' +
					'made from, read back by the skip so a change to any of them redraws.',
				// THE COMPOSITION, so a change to it cannot ship without a redraw.
				// This file's header used to say nothing but running it could catch a
				// change to the drawing — true while the Python gate was the only one,
				// since it cannot evaluate a stylesheet's cascade. But `style` is
				// already recorded here and checked from JS, where a stylesheet IS
				// readable; the hole was the escape hatch not being reused. Without
				// it, editing a `.style-*` block ships 37 shared links showing the
				// previous design indefinitely, every gate green — the exact failure
				// the header above describes as the reason this script exists.
				//
				// COMMENTS STRIPPED, and that is load-bearing rather than tidiness:
				// this file is more than half prose by volume, and digesting it whole
				// would demand an 8 MB, 37-binary regeneration for a typo in a
				// docstring. That is how a gate earns being deleted.
				css: shared.css,
				// AND THE TREE THOSE RULES ARE HUNG ON, for the same reason. The
				// stylesheet decides how a card looks only given the markup, and the
				// markup is a second file that can change on its own: reorder the
				// title and the rule, drop the `script-` class, and every committed
				// twin keeps the old arrangement with `css` unmoved. Digesting the
				// module rather than each card's output because it is the SOURCE that
				// drifts — a card's own markup already reaches the picture through
				// the byte comparison above.
				markup: shared.markup,
				// AND THE FACES. Not a gate — nothing recomputes this and nothing
				// should; see `fontDigest`. It is here so the next run can ask
				// whether the faces moved, which no other digest here can answer.
				fonts: shared.fonts,
				twins: Object.fromEntries(Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)))
			},
			null,
			'\t'
		) + '\n'
	);

	console.log(
		`wrote ${wrote.length} of ${books.length} twins` +
			(skipped ? ` (${skipped} unchanged, skipped — \`--force\` redraws them)` : '')
	);
	for (const line of wrote) console.log(`    ${line}`);
}

await main();
