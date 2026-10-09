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
 * HOW: Pango text on SVG shapes, composited by sharp — see `card-kit.mjs`,
 * which says why (Arabic, Devanagari) and how the fonts are found. Each page's
 * card is drawn from the author response it inlines, and the English quote
 * from the prerendered quote page; no trip to the API.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { authorCardUrl, authorData, cardQuote } from '../src/lib/authorCard.ts';
import {
	GOLD,
	H,
	INK,
	JPEG,
	MUTED,
	QUOTE_INK,
	RING,
	SANS,
	SERIF,
	W,
	drawAll,
	esc,
	inlined,
	paper,
	portrait,
	runAsScript,
	shadowOf,
	sharp,
	text,
	wordmark
} from './card-kit.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const LOCALES = JSON.parse(
	readFileSync(resolve(HERE, '../project.inlang/settings.json'), 'utf8')
).locales;

/** Scripts with no italic of their own: a slanted Amiri or Tiro reads as a
 *  rendering fault, so their lines are set upright. */
const UPRIGHT = new Set(['ar', 'hi', 'am', 'ko']);
const RTL = new Set(['ar']);
/** Locales whose "Read …" line carries its own quotation marks; the rest
 *  italicise the title instead. */
const MARKED = new Set(['ar', 'hi', 'uk', 'am']);

// The arch the portrait sits in, and the column beside it.
const ARCH = { w: 330, h: 430, top: 72, edge: 72 };
const RING_GAP = 8;
const COL = { w: 658 };

// ── Text ────────────────────────────────────────────────────────────────────

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

/** The portrait (or monogram) clipped to the arch. */
const archPortrait = (file, slug, name) =>
	portrait(file, {
		slug,
		name,
		w: ARCH.w,
		h: ARCH.h,
		shape: `<path d="${archPath(ARCH.w, ARCH.h)}"/>`
	});

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
				const ring = paper(
					`<path d="${archPath(ARCH.w + 2 * g, ARCH.h + 2 * g, ax - g, ARCH.top - g)}" fill="none" stroke="${RING}" stroke-width="2"/>`
				);
				const shadow = await shadowOf(
					W,
					H,
					`<path d="${archPath(ARCH.w, ARCH.h, ax, ARCH.top + 18)}" fill="rgb(60,40,10)" fill-opacity=".28"/>`,
					18
				);
				const col = rtl ? { x: ARCH.edge } : { x: ax + ARCH.w + 68 };
				const mark = await wordmark(COL.w);
				const foot = await text(
					`<span font_desc="${SANS} Medium 19" foreground="${MUTED}">${esc(footer)} · ochorus.com</span>`,
					{ width: W - 144, rtl }
				);
				const base = await sharp(ring)
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
			{
				input: await archPortrait(portraitFile, author.slug, author.name),
				left: ax,
				top: ARCH.top
			},
			...blocks
		])
		.jpeg(JPEG)
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

/** The English quote for a card, from the author's prerendered quote page. */
function quoteFor(build, slug) {
	const page = join(build, 'quotes', slug, 'index.html');
	if (!existsSync(page)) return null;
	const data = inlined(readFileSync(page, 'utf8'), `/api/library/quotes/${slug}/`);
	return data ? cardQuote(data.quotes ?? []) : null;
}

// ── Run ─────────────────────────────────────────────────────────────────────

async function main(build) {
	const messages = Object.fromEntries(
		LOCALES.map((l) => [
			l,
			JSON.parse(readFileSync(resolve(HERE, `../messages/${l}.json`), 'utf8'))
		])
	);
	const jobs = authorPages(build).map((p) => ({
		...p,
		dest: authorCardUrl(p.slug, p.locale),
		label: `${p.locale}/${p.slug}`
	}));
	await drawAll('build-author-cards', build, jobs, async ({ locale, slug, file }) => {
		const data = authorData(readFileSync(file, 'utf8'));
		if (!data) throw new Error('no author data inlined in the page');
		// A page whose language has no row falls back to the English one; its
		// titles are then English, and must not reach a card in another language.
		const { author } = data;
		const own = data.language === locale;
		const photo = author.photo_url && join(build, author.photo_url);
		const quote = locale === 'en' && author.quote_count ? quoteFor(build, slug) : null;
		return draw(
			locale,
			author,
			own,
			messages[locale],
			quote,
			photo && existsSync(photo) ? photo : null
		);
	});
}

await runAsScript(import.meta.url, 'build-author-cards', main);
