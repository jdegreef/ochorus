/**
 * Draw a share card for every prerendered AUTHOR page, in every language.
 *
 * Runs as `postbuild`, after the book and verse cards:
 *
 *     npm run build                                    # vite build, then all three
 *     node scripts/build-author-cards.mjs [buildDir]   # by hand; default ./build
 *
 * WHAT IT IS
 * An author page used to share its raw portrait, which link previews crop to a
 * 1.91:1 strip — usually through the face. The card sets the whole portrait in
 * an arch (a monogram where there is none), beside the name, the dates, a line
 * in the page's language and the counts. The English card quotes the author —
 * the first line on their quote page that reads at a glance, so ordering that
 * page is how an editor chooses it. Quotes exist only in English, so every
 * other language says "Read <their first book, in that language>" instead:
 * a card with words on it serves one language, and nothing on a Spanish card
 * is English.
 *
 * WHY PANGO, NOT SATORI
 * These cards are drawn in every interface language, Arabic and Devanagari
 * included, and satori cannot shape either. sharp carries Pango (with HarfBuzz
 * and FriBidi), which shapes, wraps and lays out right-to-left — so every card
 * is text blocks from Pango and shapes from SVG, composited by sharp. No
 * browser on the build machine.
 *
 * Pango finds fonts through fontconfig, so this writes a fontconfig file naming
 * only `scripts/fonts/pango` (cut by `scripts/fonts/cut-pango-fonts.py` from the
 * app's own @fontsource faces) and forces Pango's fontconfig backend: on macOS
 * it would otherwise use CoreText, ignore that file, and set every card in
 * Helvetica. Both are set BEFORE sharp is imported — Pango reads them once.
 *
 * THE BUILD IS THE SOURCE OF TRUTH, as for the book and verse cards: each page
 * carries the API response it was rendered from, and the English quote comes
 * from the prerendered quote page. No trip to the API. A page this cannot draw
 * gets the house card, and says so — a missing card must not fail a deploy.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { LANDSCAPE_HEIGHT as H, LANDSCAPE_WIDTH as W } from '../src/lib/coverArt.ts';
import { authorCardUrl, authorData, cardQuote } from '../src/lib/authorCard.ts';
import { initials, portraitPosition } from '../src/lib/portraits.ts';

const HERE = dirname(fileURLToPath(import.meta.url));

const FONTCONFIG = join(tmpdir(), 'ochorus-card-fonts.conf');
writeFileSync(
	FONTCONFIG,
	`<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>` +
		`<dir>${resolve(HERE, 'fonts/pango')}</dir>` +
		`<cachedir>${join(tmpdir(), 'ochorus-card-fonts-cache')}</cachedir></fontconfig>`
);
process.env.FONTCONFIG_FILE = FONTCONFIG;
process.env.PANGOCAIRO_BACKEND = 'fc';
const { default: sharp } = await import('sharp');

const LOCALES = JSON.parse(
	readFileSync(resolve(HERE, '../project.inlang/settings.json'), 'utf8')
).locales;
const FALLBACK = '/og/default.png';

const INK = '#221c14';
const GOLD = '#9c6f1e';
const RING = '#c9a86a';
const MUTED = '#6d6152';
const QUOTE_INK = '#3a3127';
const RULE = '#d9c29a';

// Every face a card can need, in fallback order: fontconfig takes each glyph
// from the first family that has it, so one description serves every script.
const SERIF = 'Fraunces, PT Serif, Amiri, Tiro Devanagari Hindi, Noto Serif Ethiopic';
const SANS = 'Hanken Grotesk, PT Sans, Noto Sans Arabic, Noto Sans Devanagari, Noto Sans Ethiopic';

/** Scripts with no italic of their own: a slanted Amiri or Tiro reads as a
 *  rendering fault, so their lines are set upright. */
const UPRIGHT = new Set(['ar', 'hi', 'am']);
const RTL = new Set(['ar']);
/** Locales whose "Read …" line carries its own quotation marks; the rest
 *  italicise the title instead. */
const MARKED = new Set(['ar', 'hi', 'uk', 'am']);

// The arch the portrait sits in, and the column beside it.
const ARCH = { w: 330, h: 430, top: 72, edge: 72 };
const RING_GAP = 8;
const COL = { w: 658 };

// ── Pango ───────────────────────────────────────────────────────────────────

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** One block of Pango markup, laid out in `width`, as a composite input. */
async function text(markup, { width, rtl = false }) {
	const { data, info } = await sharp({
		text: {
			text: markup,
			rgba: true,
			dpi: 72,
			width,
			wrap: 'word',
			align: rtl ? 'right' : 'left',
			rtl
		}
	})
		.png()
		.toBuffer({ resolveWithObject: true });
	return { data, width: info.width, height: info.height };
}

/** The name on one line where it can be, shrinking to fit before it wraps. */
async function nameBlock(name, rtl) {
	for (let size = 66; size >= 46; size -= 4) {
		const block = await text(
			`<span font_desc="${SERIF} Semi-Bold ${size}" foreground="${INK}">${esc(name)}</span>`,
			{ width: COL.w, rtl }
		);
		if (block.height < size * 1.6 || size === 46) return block;
	}
}

// ── Shapes ──────────────────────────────────────────────────────────────────

/** An arch w×h: a semicircular head, lightly rounded feet. */
const archPath = (w, h, x = 0, y = 0) => {
	const r = w / 2;
	return `M${x},${y + h - 10} V${y + r} A${r},${r} 0 0 1 ${x + w},${y + r} V${y + h - 10} Q${x + w},${y + h} ${x + w - 10},${y + h} H${x + 10} Q${x},${y + h} ${x},${y + h - 10} Z`;
};

const svg = (w, h, body) =>
	Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${body}</svg>`);

/** The portrait cropped to the arch at its focal point (the same
 *  `object-position` the page uses), or a monogram when there is none. */
async function portrait(file, slug, name) {
	const mask = svg(ARCH.w, ARCH.h, `<path d="${archPath(ARCH.w, ARCH.h)}" fill="#fff"/>`);
	let face;
	if (file) {
		const { width = 1, height = 1 } = await sharp(file).metadata();
		const scale = Math.max(ARCH.w / width, ARCH.h / height);
		const sw = Math.round(width * scale);
		const sh = Math.round(height * scale);
		const [px, py] = portraitPosition(slug)
			.split(' ')
			.map((p) => (Number.isFinite(parseFloat(p)) ? parseFloat(p) / 100 : 0.5));
		face = await sharp(file)
			.resize(sw, sh)
			.extract({
				left: Math.round((sw - ARCH.w) * px),
				top: Math.round((sh - ARCH.h) * py),
				width: ARCH.w,
				height: ARCH.h
			})
			.png()
			.toBuffer();
	} else {
		const letters = await text(
			`<span font_desc="${SERIF} Semi-Bold 130" foreground="${GOLD}">${esc(initials(name))}</span>`,
			{ width: ARCH.w }
		);
		face = await sharp(
			svg(
				ARCH.w,
				ARCH.h,
				`<defs><linearGradient id="g" x1="0" y1="0" x2=".5" y2="1"><stop offset="0" stop-color="#e9dcc2"/><stop offset="1" stop-color="#d8c49d"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/>`
			)
		)
			.composite([
				{
					input: letters.data,
					left: Math.round((ARCH.w - letters.width) / 2),
					top: Math.round((ARCH.h - letters.height) / 2)
				}
			])
			.png()
			.toBuffer();
	}
	return sharp(face)
		.composite([{ input: mask, blend: 'dest-in' }])
		.png()
		.toBuffer();
}

/** The parts of a card that depend only on its language and direction: the
 *  paper, the arch's shadow and ring, the wordmark, the rule and the footer. */
const grounds = new Map();
function ground(locale, footer) {
	if (!grounds.has(locale)) {
		grounds.set(
			locale,
			(async () => {
				const rtl = RTL.has(locale);
				const ax = rtl ? W - ARCH.edge - ARCH.w : ARCH.edge;
				const g = RING_GAP;
				const paper = svg(
					W,
					H,
					`<defs><linearGradient id="p" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#faf6ef"/><stop offset="1" stop-color="#f1e8d8"/></linearGradient></defs>` +
						`<rect width="100%" height="100%" fill="url(#p)"/>` +
						`<rect x="40" y="544" width="${W - 80}" height="3" fill="${RULE}"/>` +
						`<path d="${archPath(ARCH.w + 2 * g, ARCH.h + 2 * g, ax - g, ARCH.top - g)}" fill="none" stroke="${RING}" stroke-width="2"/>`
				);
				const shadow = await sharp(
					svg(
						W,
						H,
						`<path d="${archPath(ARCH.w, ARCH.h, ax, ARCH.top + 18)}" fill="rgb(60,40,10)" fill-opacity=".28"/>`
					)
				)
					.blur(18)
					.png()
					.toBuffer();
				const col = rtl ? { x: ARCH.edge } : { x: ax + ARCH.w + 68 };
				const mark = await text(
					`<span font_desc="${SANS} Semi-Bold 20" foreground="${GOLD}" letter_spacing="6554">OCHORUS</span>`,
					{ width: COL.w }
				);
				const foot = await text(
					`<span font_desc="${SANS} Medium 19" foreground="${MUTED}">${esc(footer)} · ochorus.com</span>`,
					{ width: W - 144, rtl }
				);
				const base = await sharp(paper)
					.composite([
						{ input: shadow, left: 0, top: 0 },
						{
							input: mark.data,
							top: ARCH.top,
							left: rtl ? col.x + COL.w - mark.width : col.x
						},
						{ input: foot.data, top: 574, left: rtl ? W - 72 - foot.width : 72 }
					])
					.png()
					.toBuffer();
				return { base, ax, col, rtl };
			})()
		);
	}
	return grounds.get(locale);
}

// ── One card ────────────────────────────────────────────────────────────────

const lifespan = (a, born) =>
	!a.birth_year ? '' : a.death_year ? `${a.birth_year}–${a.death_year}` : `${born} ${a.birth_year}`;

/** A quote can run to four lines; a "Read …" line is short, so it is set
 *  larger to hold the column. Amiri sits visibly smaller than Fraunces at the
 *  same size, so Arabic takes a step more. */
const lineSize = (locale, quoting) => (quoting ? 29 : locale === 'ar' ? 40 : 34);

const count = (n, one, many) => (n ? `${n} ${n === 1 ? one : many}` : '');

async function draw(locale, author, own, msg, quote, portraitFile) {
	const { base, ax, col, rtl } = await ground(locale, msg.author_share_footer);
	const upright = UPRIGHT.has(locale);
	// A quote is set in italic; a "Read …" line upright, with only its title in
	// italic — unless the script has no italic, when both stand upright.
	const style = quote && !upright ? 'Italic' : '';
	const at = (block) => (rtl ? col.x + COL.w - block.width : col.x);

	const blocks = [];
	let y = ARCH.top + 50;
	const place = (block, gap) => {
		y += gap;
		blocks.push({ input: block.data, top: y, left: at(block) });
		y += block.height;
	};

	place(await nameBlock(author.name, rtl), 0);
	const years = lifespan(author, msg.common_born_prefix);
	if (years) {
		place(
			await text(`<span font_desc="${SERIF} Italic 30" foreground="${GOLD}">${esc(years)}</span>`, {
				width: COL.w,
				rtl
			}),
			14
		);
	}

	let line = null;
	if (quote) {
		line = `“${esc(quote)}”`;
	} else if (own && (author.books?.[0]?.title || author.sermons?.[0]?.title)) {
		// Their first book in this language, else their first sermon — the
		// page's own first item either way.
		const title = esc(author.books?.[0]?.title || author.sermons[0].title);
		line = esc(msg.author_share_read).replace(
			'%title%',
			MARKED.has(locale) ? title : `<i>${title}</i>`
		);
	}
	if (line) {
		place(
			await text(
				`<span font_desc="${SERIF} ${style} ${lineSize(locale, !!quote)}" foreground="${QUOTE_INK}">${line}</span>`,
				{ width: COL.w, rtl }
			),
			28
		);
	}

	const counts = [
		count(author.books?.length ?? 0, msg.common_book_one, msg.common_book_many),
		count(author.sermons?.length ?? 0, msg.common_sermon_one, msg.common_sermon_many)
	]
		.filter(Boolean)
		.join(' · ');
	if (counts) {
		const c = await text(
			`<span font_desc="${SANS} Medium 20" foreground="${MUTED}">${esc(counts)}</span>`,
			{
				width: COL.w,
				rtl
			}
		);
		// Pinned to the arch's foot rather than stacked, so it lines up across
		// cards; pushed down only when a long quote reaches it.
		blocks.push({
			input: c.data,
			top: Math.max(ARCH.top + ARCH.h - c.height - 4, y + 16),
			left: at(c)
		});
	}

	return sharp(base)
		.composite([
			{ input: await portrait(portraitFile, author.slug, author.name), left: ax, top: ARCH.top },
			...blocks
		])
		.jpeg({
			// The verse cards' settings, for the verse cards' reasons.
			quality: 80,
			mozjpeg: true,
			trellisQuantisation: false,
			overshootDeringing: false,
			optimiseScans: false
		})
		.toBuffer();
}

// ── Reading the build ───────────────────────────────────────────────────────

/** Every prerendered author page, with the locale its path names. */
function authorPages(build) {
	const found = [];
	for (const locale of LOCALES) {
		const root = locale === 'en' ? join(build, 'authors') : join(build, locale, 'authors');
		if (!existsSync(root)) continue;
		for (const slug of readdirSync(root)) {
			const file = join(root, slug, 'index.html');
			if (existsSync(file)) found.push({ locale, slug, file });
		}
	}
	return found;
}

const QUOTES =
	/<script type="application\/json" data-sveltekit-fetched data-url="[^"]*\/api\/library\/quotes\/[^"]+"[^>]*>([\s\S]*?)<\/script>/;

/** The English quote for a card, from the author's prerendered quote page. */
function quoteFor(build, slug) {
	const page = join(build, 'quotes', slug, 'index.html');
	if (!existsSync(page)) return null;
	try {
		const raw = QUOTES.exec(readFileSync(page, 'utf8'))?.[1];
		return raw ? cardQuote(JSON.parse(JSON.parse(raw).body).quotes ?? []) : null;
	} catch {
		return null;
	}
}

// ── Run ─────────────────────────────────────────────────────────────────────

async function main() {
	const build = resolve(process.cwd(), process.argv[2] ?? 'build');
	const started = Date.now();
	const messages = Object.fromEntries(
		LOCALES.map((l) => [
			l,
			JSON.parse(readFileSync(resolve(HERE, `../messages/${l}.json`), 'utf8'))
		])
	);
	const pages = authorPages(build);
	const failed = [];

	async function one({ locale, slug, file }) {
		const dest = join(build, authorCardUrl(slug, locale));
		try {
			mkdirSync(dirname(dest), { recursive: true });
			const data = authorData(readFileSync(file, 'utf8'));
			if (!data) throw new Error('no author data inlined in the page');
			// A page whose language has no row falls back to the English one; its
			// titles are then English, and must not reach a card in another language.
			const { author } = data;
			const own = data.language === locale;
			const photo = author.photo_url && join(build, author.photo_url);
			const quote = locale === 'en' && author.quote_count ? quoteFor(build, slug) : null;
			writeFileSync(
				dest,
				await draw(
					locale,
					author,
					own,
					messages[locale],
					quote,
					photo && existsSync(photo) ? photo : null
				)
			);
		} catch (err) {
			failed.push(`  ${locale}/${slug} — ${err.message}`);
			await sharp(join(build, FALLBACK))
				.resize(W, H)
				.jpeg({ quality: 82 })
				.toFile(dest)
				.catch(() => {});
		}
	}
	// A pool of eight — see build-verse-cards.
	let next = 0;
	const worker = async () => {
		while (next < pages.length) await one(pages[next++]);
	};
	await Promise.all(Array.from({ length: 8 }, worker));

	if (failed.length) {
		console.warn(
			`build-author-cards: ${failed.length} page(s) got the default card:\n${failed.join('\n')}`
		);
	}
	console.log(
		`build-author-cards: ${pages.length - failed.length} cards, ${failed.length} fallbacks, ` +
			`in ${((Date.now() - started) / 1000).toFixed(1)}s`
	);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
	// A share image is never worth a failed deploy — see build-verse-cards.
	await main().catch((err) => console.warn(`build-author-cards: skipped — ${err.stack ?? err}`));
}
