/**
 * Draw a share card for every prerendered BOOK SERIES page, in every language.
 *
 * Runs as `postbuild`, after the plan cards (it stands on the same shelf):
 *
 *     npm run build                                    # vite build, then every card
 *     node scripts/build-series-cards.mjs [buildDir]   # by hand; default ./build
 *
 * A series page used to share its first volume's card, so a link to The
 * Lamplighters of Gloamhaven forwarded as one book, not a series of six. Its
 * card is now the series': its name, its promise line (or the opening of its
 * description), a gold badge with its book count, and its volumes standing on
 * the ledge the plan and home cards use.
 *
 * A series has no English fallback (a language without it 404s), so every
 * page's card is in that page's language, right-to-left for Arabic. Drawn with
 * Pango through `card-kit.mjs`, from the series response each page inlines;
 * covers are each edition's `shareImage`, as on the plan card.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { shareImage } from '../src/lib/coverArt.ts';
import { seriesCardUrl } from '../src/lib/seriesCard.ts';
import {
	BADGE,
	INK,
	JPEG,
	MUTED,
	SANS,
	SERIF,
	UPRIGHT,
	W,
	badge,
	drawAll,
	esc,
	inlined,
	ledge,
	paper,
	runAsScript,
	sharp,
	shelf,
	text,
	wordmark
} from './card-kit.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const LOCALES = JSON.parse(
	readFileSync(resolve(HERE, '../project.inlang/settings.json'), 'utf8')
).locales;
const RTL = new Set(['ar']);
const TEXT_W = 820;

/** Trimmed on a word, so a long description reads as a lede — or, in a
 *  script written without spaces (Japanese), at the limit itself. */
function lede(s, limit) {
	if (s.length <= limit) return s;
	const space = s.lastIndexOf(' ', limit);
	return `${s.slice(0, space > limit / 2 ? space : limit).replace(/[,;:—、，-]+$/, '')}…`;
}

/** The largest size at which the title fits two lines. */
async function titleBlock(title, rtl) {
	let block;
	for (const size of [54, 48, 42, 38]) {
		block = await text(
			`<span font_desc="${SERIF} Semi-Bold ${size}" foreground="${INK}">${esc(title)}</span>`,
			{ width: TEXT_W, rtl }
		);
		if (block.height <= size * 2.6) return block;
	}
	return block;
}

async function draw(locale, series, msg, build) {
	const rtl = RTL.has(locale);
	const start = (w) => (rtl ? W - 72 - w : 72);
	const mark = await wordmark(400);
	const title = await titleBlock(series.title, rtl);
	const parts = [
		{ input: mark.data, left: start(mark.width), top: 58 },
		{ input: title.data, left: start(title.width), top: 100 }
	];

	const line = series.tagline || lede(series.description || '', 110);
	if (line) {
		const slant = UPRIGHT.has(locale) || !series.tagline ? '' : 'Italic';
		const block = await text(
			`<span font_desc="${SERIF} ${slant} 22" foreground="#4a4035">${esc(line)}</span>`,
			{ width: TEXT_W, rtl }
		);
		parts.push({ input: block.data, left: start(block.width), top: 100 + title.height + 12 });
	}

	const count = series.books.length;
	parts.push({
		input: await badge(locale, count, count === 1 ? msg.common_book_one : msg.common_book_many),
		left: rtl ? 72 : W - 72 - BADGE.d,
		top: BADGE.top
	});

	const files = series.books
		.map((b) => shareImage({ slug: b.slug, language: b.language, cover_url: b.cover_url || '' })?.url)
		.filter((url) => url && /\.(jpe?g|png)$/.test(url))
		.map((url) => join(build, url))
		.filter(existsSync);
	parts.push(...(await shelf(files)), await ledge());

	const foot = await text(
		`<span font_desc="${SANS} Medium 19" foreground="${MUTED}">${esc(msg.nav_series)} · ochorus.com</span>`,
		{ width: W - 144, rtl }
	);
	parts.push({ input: foot.data, left: start(foot.width), top: 582 });

	return sharp(paper()).composite(parts).jpeg(JPEG).toBuffer();
}

/** Every prerendered series page, with the locale its path names. */
function seriesPages(build) {
	const found = [];
	for (const locale of LOCALES) {
		const root = locale === 'en' ? join(build, 'series') : join(build, locale, 'series');
		if (!existsSync(root)) continue;
		for (const slug of readdirSync(root)) {
			const file = join(root, slug, 'index.html');
			if (existsSync(file)) found.push({ locale, slug, file });
		}
	}
	return found;
}

async function main(build) {
	const messages = Object.fromEntries(
		LOCALES.map((l) => [l, JSON.parse(readFileSync(resolve(HERE, `../messages/${l}.json`), 'utf8'))])
	);
	const jobs = seriesPages(build).map((p) => ({
		...p,
		dest: seriesCardUrl(p.slug, p.locale),
		label: `${p.locale}/${p.slug}`
	}));
	await drawAll('build-series-cards', build, jobs, async ({ locale, slug, file }) => {
		const series = inlined(readFileSync(file, 'utf8'), `/api/library/series/${slug}/\\?language=${locale}`);
		if (!series?.books) throw new Error('no series data inlined in the page');
		return draw(locale, series, messages[locale], build);
	});
}

await runAsScript(import.meta.url, 'build-series-cards', main);
