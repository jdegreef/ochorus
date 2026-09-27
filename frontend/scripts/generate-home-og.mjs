/**
 * Draw the home page's share card, one per interface language.
 *
 * Output: frontend/static/og/home/<locale>.jpg (1200x630, `homeShareCardUrl`),
 * committed.
 * NOT part of the build or CI; run it by hand when the shelf, the copy or the
 * counts should move:
 *
 *     cd frontend && npm run og:home
 *
 * WHAT IT IS
 * The home URL is the link people share most, and it used to preview as
 * `og/default.png` — a wordmark on a gradient, with not one book in it. This
 * card is the library itself: seven real covers standing on a ledge under a
 * headline, with the edition's counts above and the footer tagline below.
 *
 * ONE PER LANGUAGE, because a card with words in it serves one language — the
 * covers' own rule. The Spanish home page shows Spanish copy, Spanish counts
 * and the Spanish editions' covers; nothing on a card is borrowed from another
 * language. The copy is the `home_share_*` messages plus `footer_tagline`, read
 * straight from the catalogues, so translating a string is how a card changes.
 *
 * THE COVERS ARE THE ONES THE BOOK PAGES SHARE. Each is `shareImage()` of a
 * published edition in that language — the designed raster where the cover is
 * one, the edition's twin (`/covers/<lang>/<slug>.png`) where it is a plate or
 * a painting — so a cover here is exactly the picture that book's own link
 * preview shows, already set in its own script. English's shelf is picked by
 * hand (`SHELF`); every other language takes its most colourful covers, one per
 * author first — see `colourfulness`.
 *
 * THE COUNTS ARE ROUNDED DOWN ("140+"), because this is a committed file drawn
 * on a day and read for months: a floor stays true as the library grows. They
 * are the language's own published books and sermons — never the whole
 * library's, which would promise a Luganda reader books that are not there.
 *
 * WHY CHROMIUM: the headline is set in Amiri, Tiro and Noto Ethiopic as well
 * as Fraunces, and satori cannot shape Arabic or Devanagari.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';
import sharp from 'sharp';

import { LANDSCAPE_HEIGHT as H, LANDSCAPE_WIDTH as W, shareImage } from '../src/lib/coverArt.ts';
import { LIVE_LOCALES } from '../src/lib/live-locales.generated.ts';
import { homeShareCardUrl } from '../src/lib/homeShareCard.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const STATIC = resolve(HERE, '../static');
const MESSAGES = resolve(HERE, '../messages');
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
const MODULES = resolve(HERE, '../node_modules');
const LOCALES = JSON.parse(
	readFileSync(resolve(HERE, '../project.inlang/settings.json'), 'utf8')
).locales;

/** The covers to lead with, best first; the first one found stands in the
 *  middle of the shelf. Slugs, so each language takes its own edition. */
const SHELF = [
	'the-secret-of-guidance',
	'the-god-of-all-comfort',
	'jesus-himself-2',
	'humility-2',
	'the-inner-chamber',
	'men-of-prayer-2',
	'women-who-moved-heaven-2',
	'pilgrims-progress',
	'absolute-surrender',
	'all-of-grace',
	'the-christians-secret-of-a-happy-life-4'
];
const ON_SHELF = 7;

/** The fontsource subset a locale's copy is written in; null for Latin. From
 *  the locale's likely script rather than a list of codes, so a new language
 *  in a known script needs nothing here. (`coverStyles.scriptOf` is the cover
 *  table and has no Ethiopic — covers do not need correcting for it.) */
const SUBSET = {
	Arab: 'arabic',
	Deva: 'devanagari',
	Cyrl: 'cyrillic',
	Ethi: 'ethiopic'
};
const scriptOf = (locale) => SUBSET[new Intl.Locale(locale).maximize().script] ?? null;

// ── The content ─────────────────────────────────────────────────────────────

const rows = (dir, model) =>
	readdirSync(resolve(CONTENT, dir))
		.filter((f) => f.endsWith('.json'))
		.sort()
		.map((f) => JSON.parse(readFileSync(resolve(CONTENT, dir, f), 'utf8'))[0])
		.filter((r) => r.model === model && r.fields.is_published !== false)
		.map((r) => r.fields);

const BOOKS = rows('books', 'library.book');
const SERMONS = rows('sermons', 'library.sermon');

/** "140+" for a count that will only grow; the exact figure while it is small
 *  enough that a floor would undersell it. */
const atLeast = (n) => isolate(n >= 20 ? `${Math.floor(n / 10) * 10}+` : String(n));
/** Left-to-right isolated, so an Arabic line keeps "40+" rather than
 *  reordering it to "+40". Invisible everywhere else. */
const isolate = (s) => `\u2066${s}\u2069`;

/**
 * How colourful a cover reads at a glance — Hasler & Süsstrunk's metric, on a
 * thumbnail. The designed English covers are picked by hand (`SHELF`); a
 * translated edition mostly wears a twin, and a shelf of twins ranked the same
 * way came out as five pale paintings in a row. So the other languages lead
 * with their most colourful covers instead, and `SHELF` only breaks ties.
 */
async function colourfulness(file) {
	const { data } = await sharp(file).resize(48, 64, { fit: 'fill' }).removeAlpha().raw().toBuffer({
		resolveWithObject: true
	});
	const rg = [];
	const yb = [];
	for (let i = 0; i < data.length; i += 3) {
		rg.push(data[i] - data[i + 1]);
		yb.push((data[i] + data[i + 1]) / 2 - data[i + 2]);
	}
	const stats = (xs) => {
		const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
		return [mean, Math.sqrt(xs.reduce((a, x) => a + (x - mean) ** 2, 0) / xs.length)];
	};
	const [mrg, srg] = stats(rg);
	const [myb, syb] = stats(yb);
	return Math.hypot(srg, syb) + 0.3 * Math.hypot(mrg, myb);
}

/** The files on this language's shelf, in slot order. */
async function shelf(language) {
	const editions = BOOKS.filter((b) => b.language === language)
		.map((b) => ({
			slug: b.slug,
			author: b.author[0],
			url: shareImage({ ...b, cover_url: b.cover_url || '' })?.url
		}))
		.filter(
			(b) => b.url && /\.(jpe?g|png)$/.test(b.url) && existsSync(resolve(STATIC, `.${b.url}`))
		)
		.map((b) => ({ ...b, file: resolve(STATIC, `.${b.url}`) }));
	const rank = (slug) => (SHELF.includes(slug) ? SHELF.indexOf(slug) : SHELF.length);
	if (language !== 'en') {
		for (const e of editions) e.score = Math.round(await colourfulness(e.file));
	}
	const ranked = editions.sort(
		(a, b) =>
			(language === 'en' ? 0 : b.score - a.score) ||
			rank(a.slug) - rank(b.slug) ||
			a.slug.localeCompare(b.slug)
	);
	// One book per author before anyone gets a second: a series of plates in the
	// same livery would otherwise fill the shelf. English is picked by hand.
	const seen = new Set();
	const first =
		language === 'en' ? ranked : ranked.filter((e) => !seen.has(e.author) && seen.add(e.author));
	const picks = [...first, ...ranked.filter((e) => !first.includes(e))].slice(0, ON_SHELF);
	// The best in the middle, then alternating outward, so the edges — which the
	// frame crops — get the last picks.
	const mid = Math.floor((picks.length - 1) / 2);
	const slots = [];
	picks.forEach((p, i) => (slots[mid + (i % 2 ? -1 : 1) * Math.ceil(i / 2)] = p));
	return slots.map((p) => p.file);
}

// ── The page ────────────────────────────────────────────────────────────────

const dataUri = (file, mime) => `data:${mime};base64,${readFileSync(file).toString('base64')}`;

/** Every @font-face in one fontsource stylesheet whose subset is wanted, with
 *  its woff2 inlined (Chromium is rendering a string; there is no directory for
 *  a relative url() to resolve against). */
function faces(sheet, subsets) {
	const file = resolve(MODULES, sheet);
	const want = new RegExp(`url\\(\\./files/[^)]*-(${subsets.join('|')})-`);
	return readFileSync(file, 'utf8')
		.split('@font-face')
		.slice(1)
		.map((b) => `@font-face${b.slice(0, b.indexOf('}') + 1)}`)
		.filter((b) => want.test(b))
		.map((b) =>
			b
				.replace(/,\s*url\(\.\/files\/[^)]+\)\s*format\('woff'\)/g, '')
				.replace(
					/url\(\.\/files\/([^)]+)\)/g,
					(_m, name) => `url(${dataUri(resolve(dirname(file), 'files', name), 'font/woff2')})`
				)
		)
		.join('');
}

function fontCss(script) {
	const subsets = ['latin', 'latin-ext', ...(script ? [script] : [])];
	if (script === 'cyrillic') subsets.push('cyrillic-ext');
	const sheets = [
		'@fontsource-variable/fraunces/opsz.css',
		'@fontsource-variable/fraunces/opsz-italic.css',
		'@fontsource-variable/hanken-grotesk/index.css'
	];
	if (script === 'arabic')
		sheets.push('@fontsource/amiri/700.css', '@fontsource/noto-sans-arabic/400.css');
	if (script === 'devanagari')
		sheets.push(
			'@fontsource/tiro-devanagari-hindi/400.css',
			'@fontsource/noto-sans-devanagari/400.css'
		);
	if (script === 'ethiopic')
		sheets.push(
			'@fontsource/noto-serif-ethiopic/700.css',
			'@fontsource/noto-sans-ethiopic/400.css'
		);
	if (script === 'cyrillic')
		sheets.push('@fontsource/pt-serif/700.css', '@fontsource/pt-sans/400.css');
	return sheets.map((s) => faces(s, subsets)).join('');
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function page(locale, msg, covers) {
	const script = scriptOf(locale);
	const counts = msg.home_share_counts
		.replace('{books}', atLeast(BOOKS.filter((b) => b.language === locale).length))
		.replace('{sermons}', atLeast(SERMONS.filter((s) => s.language === locale).length))
		.replace('{languages}', isolate(String(LIVE_LOCALES.length)));
	// Italic is a Latin idea; Amiri, Tiro and Noto Ethiopic have none, and a
	// synthesised slant on them reads as a rendering fault. Colour carries it.
	const accentStyle = !script || script === 'cyrillic' ? 'italic' : 'normal';
	return `<!doctype html><html lang="${locale}" dir="${script === 'arabic' ? 'rtl' : 'ltr'}"><head><meta charset="utf-8"><style>
${fontCss(script)}
*{margin:0;box-sizing:border-box}
html,body{width:${W}px;height:${H}px;overflow:hidden}
body{background:linear-gradient(180deg,#faf6ef 0%,#f1e8d8 100%);font-family:'Hanken Grotesk Variable','Noto Sans Arabic','Noto Sans Devanagari','Noto Sans Ethiopic','PT Sans',sans-serif}
.top{position:absolute;inset-inline:72px;top:58px;display:flex;justify-content:space-between;align-items:baseline}
.k{color:#9c6f1e;letter-spacing:.32em;font-size:20px;font-weight:600;direction:ltr}
.s{color:#6d6152;font-size:19px;font-weight:500}
h1{position:absolute;inset-inline:72px;top:104px;white-space:nowrap;color:#221c14;font-family:'Fraunces Variable','Amiri','Tiro Devanagari Hindi','Noto Serif Ethiopic','PT Serif',serif;font-size:62px;font-weight:600;line-height:1.1;letter-spacing:-.01em}
h1 em{font-style:${accentStyle};font-weight:400;color:#9c6f1e}
.shelf{position:absolute;left:0;right:0;top:246px;height:300px;display:flex;justify-content:center;align-items:flex-end;gap:26px;direction:ltr;overflow:hidden}
.shelf img{height:270px;border-radius:4px;box-shadow:0 14px 26px rgba(60,40,10,.32),0 2px 4px rgba(60,40,10,.3)}
.shelf img:nth-child(odd){height:252px}
.ledge{position:absolute;left:40px;right:40px;top:544px;height:16px;border-radius:3px;background:linear-gradient(180deg,#b58a52,#7d5a2e);box-shadow:0 10px 18px rgba(60,40,10,.28)}
.f{position:absolute;inset-inline:72px;top:582px;color:#6d6152;font-size:19px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
</style></head><body>
<div class="top"><div class="k">OCHORUS</div><div class="s">${esc(counts)}</div></div>
<h1>${esc(msg.home_share_title_lead)} <em>${esc(msg.home_share_title_accent)}</em></h1>
<div class="shelf">${covers.map((c) => `<img src="${dataUri(c, c.endsWith('.png') ? 'image/png' : 'image/jpeg')}">`).join('')}</div>
<div class="ledge"></div>
<div class="f">${esc(msg.footer_tagline)} · ochorus.com</div>
</body></html>`;
}

// ── Draw ────────────────────────────────────────────────────────────────────

const browser = await chromium.launch();
const tab = await browser.newPage({
	viewport: { width: W, height: H },
	deviceScaleFactor: 1
});
for (const locale of LOCALES) {
	const msg = JSON.parse(readFileSync(resolve(MESSAGES, `${locale}.json`), 'utf8'));
	const covers = await shelf(locale);
	if (covers.length < 3) throw new Error(`${locale}: only ${covers.length} shareable covers`);
	await tab.setContent(page(locale, msg, covers), { waitUntil: 'load' });
	await tab.evaluate(() => document.fonts.ready);
	// One line, always: shrink a long headline until it fits the measure rather
	// than let it wrap into the covers.
	await tab.evaluate(() => {
		const fit = (el, size, min) => {
			while (el.scrollWidth > el.clientWidth && size > min) el.style.fontSize = `${(size -= 1)}px`;
		};
		fit(document.querySelector('h1'), 62, 36);
		fit(document.querySelector('.f'), 19, 14);
	});
	const png = await tab.screenshot({ type: 'png' });
	const jpg = await sharp(png).jpeg({ quality: 84, mozjpeg: true }).toBuffer();
	const file = resolve(STATIC, `.${homeShareCardUrl(locale)}`);
	mkdirSync(dirname(file), { recursive: true });
	if (!existsSync(file) || !readFileSync(file).equals(jpg)) writeFileSync(file, jpg);
	console.log(
		`  ✓ ${homeShareCardUrl(locale)}  (${covers.length} covers, ${(jpg.length / 1024).toFixed(0)} KB)`
	);
}
await browser.close();
