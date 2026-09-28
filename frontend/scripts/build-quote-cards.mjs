/**
 * Draw a share card for every prerendered QUOTE page.
 *
 * Runs as `postbuild`, after the author cards:
 *
 *     npm run build                                   # vite build, then every card
 *     node scripts/build-quote-cards.mjs [buildDir]   # by hand; default ./build
 *
 * TWO CARDS, BY PAGE
 * - An author's quote page (and an author-on-a-topic page) shares ONE QUOTE:
 *   set large in italic, signed with the writer's portrait, name and exact
 *   source — book and chapter — beside that book's cover. The source is what
 *   these pages are for ("each quote traced to its page"), so the card shows it.
 * - A topic page ("Quotes on Prayer") gathers many writers, which one quote
 *   cannot show: its card names the topic and its verse, sets a row of the
 *   writers who speak to it with their counts, and features one quote beside.
 *
 * The quote is always the page's first line short enough to set whole
 * (`authorCard.cardQuote`) — for a topic, from the writer who says the most on
 * it — so the order of a quote page is how an editor chooses its card.
 *
 * English only, because the quote pages are: no locale prefix prerenders them.
 * Drawn with Pango like the author cards, through `card-kit.mjs`, from the API
 * response each page inlines; covers are each book's own `Book.image`.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

import { cardQuote } from '../src/lib/authorCard.ts';
import { featuredQuote, quoteCardUrl } from '../src/lib/quoteShareCard.ts';
import {
	GOLD,
	H,
	INK,
	JPEG,
	MUTED,
	RING,
	SANS,
	SERIF,
	W,
	bookCovers,
	circle,
	drawAll,
	esc,
	inlined,
	paper,
	portrait,
	ringAround,
	runAsScript,
	shadowOf,
	sharp,
	svg,
	text,
	wordmark
} from './card-kit.mjs';

const FOOT_Y = 574;
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

// ── Pieces ──────────────────────────────────────────────────────────────────

/** The footer line, at the foot of the paper. */
const footer = async (line) =>
	text(
		`<span font_desc="${SANS} Medium 19" foreground="${MUTED}">${esc(line)} · ochorus.com</span>`,
		{
			width: W - 144
		}
	);

/** A round portrait of diameter `d` with its ring, as composite inputs at (x, y). */
async function face(photo, author, d, x, y, ringColour = RING, gap = 3, stroke = 2) {
	const pic = await portrait(photo, {
		slug: author.slug,
		name: author.name,
		w: d,
		h: d,
		shape: circle(d)
	});
	return [
		{ input: svg(W, H, ringAround(x, y, d, gap, stroke, ringColour)), left: 0, top: 0 },
		{ input: pic, left: x, top: y }
	];
}

/** The largest size at which `markup(size)` fits `height`, stepping down. */
async function fitted(markup, sizes, width, height) {
	let block;
	for (const size of sizes) {
		block = await text(markup(size), { width });
		if (block.height <= height) return block;
	}
	return block;
}

/** A quote too long for any card is cut at a word, never mid-word. */
const clip = (t, max = 220) =>
	t.length <= max ? t : `${t.slice(0, t.slice(0, max).lastIndexOf(' '))}…`;

/** A cover standing slightly turned, with its shadow, drawn once per book. */
const covers = new Map();
function standing(file) {
	if (!covers.has(file)) {
		covers.set(
			file,
			(async () => {
				const CH = 360;
				const { width = 3, height = 4 } = await sharp(file).metadata();
				const cw = Math.round((CH * width) / height);
				const B = 40;
				const round = svg(cw, CH, `<rect width="${cw}" height="${CH}" rx="5" fill="#fff"/>`);
				const cover = await sharp(file)
					.resize(cw, CH, { fit: 'fill' })
					.composite([{ input: round, blend: 'dest-in' }])
					.png()
					.toBuffer();
				const shadow = await shadowOf(
					cw + 2 * B,
					CH + 2 * B,
					`<rect x="${B}" y="${B + 16}" width="${cw}" height="${CH}" rx="5" fill="rgb(60,40,10)" fill-opacity=".32"/>`,
					16
				);
				const piece = await sharp(shadow)
					.composite([{ input: cover, left: B, top: B }])
					.png()
					.toBuffer();
				// A second pipeline: sharp rotates before it composites.
				const turned = await sharp(piece)
					.rotate(3, { background: { r: 0, g: 0, b: 0, alpha: 0 } })
					.png()
					.toBuffer({ resolveWithObject: true });
				return { data: turned.data, width: turned.info.width, height: turned.info.height };
			})()
		);
	}
	return covers.get(file);
}

// ── A: one quote ────────────────────────────────────────────────────────────

async function quoteCard({ author, quote, count, topic }, build, coverFiles) {
	const coverFile = quote.source?.kind === 'chapter' ? coverFiles.get(quote.source.slug) : null;
	const width = coverFile ? 720 : 1056;
	const said = clip(quote.text);
	const block = await fitted(
		(size) => `<span font_desc="${SERIF} Italic ${size}" foreground="${INK}">${esc(said)}</span>`,
		said.length < 70 ? [52, 46, 40] : said.length < 110 ? [44, 40, 36] : [36, 32, 28],
		width,
		270
	);
	const mark = await text(`<span font_desc="${SERIF} 110" foreground="#d9c29a">“</span>`, {
		width: 100
	});
	// The quote and its mark, centred as one in the band above the signature.
	const top = 100 + Math.round((320 - (block.height + 40)) / 2);

	const photo = author.photo_url && join(build, author.photo_url);
	const signature = [
		...(await face(photo && existsSync(photo) ? photo : null, author, 64, 72, 440)),
		{
			input: (
				await text(
					`<span font_desc="${SERIF} Semi-Bold 26" foreground="${INK}">${esc(author.name)}</span>`,
					{
						width: 800
					}
				)
			).data,
			left: 156,
			top: 442
		}
	];
	if (quote.source?.work) {
		const where = [`<span font_desc="${SERIF} Italic 18">${esc(quote.source.work)}</span>`];
		if (quote.source.title && quote.source.title !== quote.source.work) {
			where.push(esc(quote.source.title));
		}
		signature.push({
			input: (
				await text(
					`<span font_desc="${SANS} Medium 18" foreground="${MUTED}">${where.join(' · ')}</span>`,
					{ width: 700 }
				)
			).data,
			left: 156,
			top: 476
		});
	}

	const n = plural(count, 'quote', 'quotes');
	const foot = await footer(
		topic
			? `${n} from ${author.name} on ${topic.title}, each traced to its page`
			: `${n} from ${author.name}, each traced to its page`
	);
	const cover = coverFile ? await standing(coverFile) : null;

	return sharp(paper())
		.composite([
			{ input: (await wordmark(400)).data, left: 72, top: 58 },
			{ input: mark.data, left: 68, top: top - 20 },
			{ input: block.data, left: 72, top: top + 40 },
			...signature,
			...(cover
				? [
						{
							input: cover.data,
							left: 1010 - Math.round(cover.width / 2),
							top: 270 - Math.round(cover.height / 2)
						}
					]
				: []),
			{ input: foot.data, left: 72, top: FOOT_Y }
		])
		.jpeg(JPEG)
		.toBuffer();
}

// ── C: a topic ──────────────────────────────────────────────────────────────

async function topicCard({ topic, authors }, build, portraits) {
	// The topic response names each writer but not their portrait; their own
	// quote page does.
	const photoOf = (a) => {
		const url = a.photo_url || portraits.get(a.slug);
		const file = url && join(build, url);
		return file && existsSync(file) ? file : null;
	};
	const voices = [...authors].sort((a, b) => b.count - a.count);
	const total = voices.reduce((n, v) => n + v.count, 0);

	const lead = await text(`<span font_desc="${SERIF} 30" foreground="${MUTED}">Quotes on</span>`, {
		width: 540
	});
	const title = await fitted(
		(size) =>
			`<span font_desc="${SERIF} Semi-Bold ${size}" foreground="${INK}">${esc(topic.title)}</span>`,
		[96, 84, 72, 60, 52],
		540,
		130
	);
	const parts = [
		{ input: (await wordmark(400)).data, left: 72, top: 58 },
		{ input: lead.data, left: 72, top: 96 },
		{ input: title.data, left: 70, top: 132 }
	];
	let y = 132 + title.height + 18;
	if (topic.scripture_text) {
		const verse = await text(
			`<span font_desc="${SERIF} Italic 22" foreground="${GOLD}">“${esc(topic.scripture_text)}”</span>` +
				(topic.scripture_ref
					? `<span font_desc="${SANS} Medium 20" foreground="${GOLD}">  — ${esc(topic.scripture_ref)}</span>`
					: ''),
			{ width: 540 }
		);
		parts.push({ input: verse.data, left: 72, top: y });
		y += verse.height;
	}

	// The writers who speak to it, most first; a paper-coloured ring keeps
	// overlapping faces apart.
	const faces = voices.filter((v) => photoOf(v.author)).slice(0, 5);
	const faceY = Math.max(y + 34, 318);
	for (const [i, v] of faces.entries()) {
		parts.push(
			...(await face(photoOf(v.author), v.author, 64, 72 + i * 52, faceY, '#faf6ef', 0, 3))
		);
	}
	const tally = await text(
		`<span font_desc="${SANS} Medium 20" foreground="#4a4035">${plural(voices.length, 'voice', 'voices')} · ${plural(total, 'quote', 'quotes')}</span>`,
		{ width: 540 }
	);
	parts.push({ input: tally.data, left: 72, top: faceY + (faces.length ? 80 : 0) });

	// The featured quote, on its own card.
	const featured = featuredQuote(voices, cardQuote);
	if (featured) {
		const box = { x: 640, y: 96, w: 488, h: 330 };
		const shade = await shadowOf(
			W,
			H,
			`<rect x="${box.x}" y="${box.y + 14}" width="${box.w}" height="${box.h}" rx="10" fill="rgb(60,40,10)" fill-opacity=".14"/>`,
			15
		);
		const said = await fitted(
			(size) =>
				`<span font_desc="${SERIF} Italic ${size}" foreground="${INK}"><span foreground="${RING}">“</span>${esc(featured.text)}<span foreground="${RING}">”</span></span>`,
			[31, 28, 25, 22],
			box.w - 72,
			box.h - 130
		);
		const name = await text(
			`<span font_desc="${SERIF} Semi-Bold 22" foreground="${INK}">${esc(featured.author.name)}</span>`,
			{ width: box.w - 140 }
		);
		parts.push(
			{ input: shade, left: 0, top: 0 },
			{
				input: svg(
					W,
					H,
					`<rect x="${box.x}" y="${box.y}" width="${box.w}" height="${box.h}" rx="10" fill="#fffdf8"/>`
				),
				left: 0,
				top: 0
			},
			{ input: said.data, left: box.x + 36, top: box.y + 34 },
			...(await face(
				photoOf(featured.author),
				featured.author,
				48,
				box.x + 36,
				box.y + box.h - 82
			)),
			{
				input: name.data,
				left: box.x + 98,
				top: box.y + box.h - 58 - Math.round(name.height / 2) + 4
			}
		);
	}

	parts.push({
		input: (await footer('What the classic Christian writers said — each quote traced to its page'))
			.data,
		left: 72,
		top: FOOT_Y
	});
	return sharp(paper()).composite(parts).jpeg(JPEG).toBuffer();
}

// ── Reading the build ───────────────────────────────────────────────────────

const dirs = (p) =>
	existsSync(p)
		? readdirSync(p, { withFileTypes: true })
				.filter((e) => e.isDirectory())
				.map((e) => e.name)
		: [];
const page = (...parts) => {
	const file = join(...parts, 'index.html');
	return existsSync(file) ? readFileSync(file, 'utf8') : null;
};

/** Every quote page the build holds, as a job to draw. */
function quotePages(build) {
	const root = join(build, 'quotes');
	const jobs = [];
	for (const topic of dirs(join(root, 'topics'))) {
		jobs.push({ kind: 'topic', topic, dest: quoteCardUrl({ topic }), label: `topics/${topic}` });
	}
	for (const author of dirs(root).filter((d) => d !== 'topics')) {
		jobs.push({ kind: 'author', author, dest: quoteCardUrl({ author }), label: author });
		for (const topic of dirs(join(root, author))) {
			jobs.push({
				kind: 'author',
				author,
				topic,
				dest: quoteCardUrl({ author, topic }),
				label: `${author}/${topic}`
			});
		}
	}
	return jobs;
}

/** Author slug → portrait URL, from each writer's prerendered quote page. */
function quotePortraits(build) {
	const root = join(build, 'quotes');
	const found = new Map();
	for (const slug of dirs(root).filter((d) => d !== 'topics')) {
		const html = page(root, slug);
		const url = html && inlined(html, `/api/library/quotes/${slug}/`)?.author?.photo_url;
		if (url) found.set(slug, url);
	}
	return found;
}

async function main(build) {
	const coverFiles = bookCovers(build);
	const portraits = quotePortraits(build);
	await drawAll('build-quote-cards', build, quotePages(build), async (job) => {
		const root = join(build, 'quotes');
		if (job.kind === 'topic') {
			const html = page(root, 'topics', job.topic);
			const data = html && inlined(html, `/api/library/quote-topics/${job.topic}/`);
			if (!data?.topic) throw new Error('no topic data inlined in the page');
			return topicCard(data, build, portraits);
		}
		const path = job.topic ? `${job.author}/${job.topic}` : job.author;
		const html = page(root, ...path.split('/'));
		const data = html && inlined(html, `/api/library/quotes/${path}/`);
		if (!data?.author || !data.quotes?.length) throw new Error('no quotes inlined in the page');
		const text = cardQuote(data.quotes);
		const quote = (text && data.quotes.find((q) => q.text.trim() === text)) || data.quotes[0];
		return quoteCard(
			{ author: data.author, quote, count: data.quotes.length, topic: data.topic },
			build,
			coverFiles
		);
	});
}

await runAsScript(import.meta.url, 'build-quote-cards', main);
