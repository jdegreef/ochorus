/**
 * What the Pango-drawn share cards share: the font setup, text blocks, shapes,
 * portraits, the JPEG settings and the run loop. Used by
 * `build-author-cards.mjs` and `build-quote-cards.mjs`.
 *
 * WHY PANGO, NOT SATORI
 * Some of these cards are drawn in every interface language, Arabic and
 * Devanagari included, and satori cannot shape either. sharp carries Pango (with
 * HarfBuzz and FriBidi), which shapes, wraps and lays out right-to-left — so a
 * card is text blocks from Pango and shapes from SVG, composited by sharp. No
 * browser on the build machine.
 *
 * Pango finds fonts through fontconfig, so this writes a fontconfig file naming
 * only `scripts/fonts/pango` (cut by `scripts/fonts/cut-pango-fonts.py` from the
 * app's own @fontsource faces) and forces Pango's fontconfig backend: on macOS
 * it would otherwise use CoreText, ignore that file, and set every card in
 * Helvetica. Both are set BEFORE sharp is imported — Pango reads them once — so
 * a card script must take `sharp` from here rather than import it itself.
 *
 * THE BUILD IS THE SOURCE OF TRUTH. Every card is drawn from the API response
 * its prerendered page inlines — no trip to the API — and a page a script
 * cannot draw gets the house card and a warning: a share image is never worth
 * a failed deploy.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '../src/lib/coverArt.ts';
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
export const { default: sharp } = await import('sharp');

export const W = LANDSCAPE_WIDTH;
export const H = LANDSCAPE_HEIGHT;

export const INK = '#221c14';
export const GOLD = '#9c6f1e';
export const RING = '#c9a86a';
export const MUTED = '#6d6152';
export const QUOTE_INK = '#3a3127';
export const RULE = '#d9c29a';

// Every face a card can need, in fallback order: fontconfig takes each glyph
// from the first family that has it, so one description serves every script.
export const SERIF = 'Fraunces, PT Serif, Amiri, Tiro Devanagari Hindi, Noto Serif Ethiopic';
export const SANS =
	'Hanken Grotesk, PT Sans, Noto Sans Arabic, Noto Sans Devanagari, Noto Sans Ethiopic';

// ── Text ────────────────────────────────────────────────────────────────────

export const esc = (s) =>
	String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** One block of Pango markup, laid out in `width`, as a composite input. */
export async function text(markup, { width, rtl = false, align }) {
	const { data, info } = await sharp({
		text: {
			text: markup,
			rgba: true,
			dpi: 72,
			width,
			wrap: 'word',
			align: align ?? (rtl ? 'right' : 'left'),
			rtl
		}
	})
		.png()
		.toBuffer({ resolveWithObject: true });
	return { data, width: info.width, height: info.height };
}

/** The spaced gold wordmark every card carries. */
export const wordmark = (width) =>
	text(
		`<span font_desc="${SANS} Semi-Bold 20" foreground="${GOLD}" letter_spacing="6554">OCHORUS</span>`,
		{ width }
	);

// ── Shapes ──────────────────────────────────────────────────────────────────

export const svg = (w, h, body) =>
	Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${body}</svg>`);

/** The card's paper and the rule above its footer — the ground every
 *  parchment card (home, verse, author, quote) stands on. */
export const paper = (extra = '') =>
	svg(
		W,
		H,
		`<defs><linearGradient id="p" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#faf6ef"/><stop offset="1" stop-color="#f1e8d8"/></linearGradient></defs>` +
			`<rect width="100%" height="100%" fill="url(#p)"/>` +
			`<rect x="40" y="544" width="${W - 80}" height="3" fill="${RULE}"/>` +
			extra
	);

/**
 * A portrait cropped to w×h at its focal point (the same `object-position` the
 * site uses), clipped to `shape` — an SVG path body drawn in white — or, with
 * no portrait, a monogram on a warm ground.
 */
export async function portrait(file, { slug, name, w, h, shape }) {
	let face;
	if (file) {
		const { width = 1, height = 1 } = await sharp(file).metadata();
		const scale = Math.max(w / width, h / height);
		const sw = Math.round(width * scale);
		const sh = Math.round(height * scale);
		const [px, py] = portraitPosition(slug)
			.split(' ')
			.map((p) => (Number.isFinite(parseFloat(p)) ? parseFloat(p) / 100 : 0.5));
		face = await sharp(file)
			.resize(sw, sh)
			.extract({
				left: Math.round((sw - w) * px),
				top: Math.round((sh - h) * py),
				width: w,
				height: h
			})
			.png()
			.toBuffer();
	} else {
		const letters = await text(
			`<span font_desc="${SERIF} Semi-Bold ${Math.round(Math.min(w, h) * 0.39)}" foreground="${GOLD}">${esc(initials(name))}</span>`,
			{ width: w, align: 'centre' }
		);
		face = await sharp(
			svg(
				w,
				h,
				`<defs><linearGradient id="g" x1="0" y1="0" x2=".5" y2="1"><stop offset="0" stop-color="#e9dcc2"/><stop offset="1" stop-color="#d8c49d"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/>`
			)
		)
			.composite([
				{
					input: letters.data,
					left: Math.round((w - letters.width) / 2),
					top: Math.round((h - letters.height) / 2)
				}
			])
			.png()
			.toBuffer();
	}
	return sharp(face)
		.composite([{ input: svg(w, h, shape.replace('/>', ' fill="#fff"/>')), blend: 'dest-in' }])
		.png()
		.toBuffer();
}

/** A circle's SVG body, for `portrait`'s `shape`. */
export const circle = (d) => `<circle cx="${d / 2}" cy="${d / 2}" r="${d / 2}"/>`;

/** A thin ring drawn around a circular portrait of diameter `d` at (x, y). */
export const ringAround = (x, y, d, gap = 3, stroke = 2, colour = RING) =>
	`<circle cx="${x + d / 2}" cy="${y + d / 2}" r="${d / 2 + gap}" fill="none" stroke="${colour}" stroke-width="${stroke}"/>`;

/** A soft shadow for a shape at (0,0), blurred by `blur`. */
export const shadowOf = async (w, h, body, blur) =>
	sharp(svg(w, h, body))
		.blur(blur)
		.png()
		.toBuffer();

// ── Output ──────────────────────────────────────────────────────────────────

/** mozjpeg's tables without its trellis/scan search: measured over all 887
 *  verse cards, 46 MB in 10 s against full mozjpeg's 41 MB in 26 s and libjpeg's
 *  55 MB in 9 s. Every deploy pays the time; the bytes, once. */
export const JPEG = {
	quality: 80,
	mozjpeg: true,
	trellisQuantisation: false,
	overshootDeringing: false,
	optimiseScans: false
};

// ── Reading the build ───────────────────────────────────────────────────────

/** The body of the first response a page inlined from an API path matching
 *  `path` (a RegExp source) that answered below 400, parsed; null if none. */
export function inlined(html, path) {
	const re = new RegExp(
		`<script type="application/json" data-sveltekit-fetched data-url="[^"]*${path}"[^>]*>([\\s\\S]*?)</script>`,
		'g'
	);
	for (const [, raw] of html.matchAll(re)) {
		try {
			const response = JSON.parse(raw);
			if ((response.status ?? 200) < 400) return JSON.parse(response.body);
		} catch {
			/* not this one */
		}
	}
	return null;
}

const LD = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;

/** Book slug → the cover its English page names (its `Book.image`), as a file
 *  in the build — the picture that book's own link preview shows. */
export function bookCovers(build) {
	const found = new Map();
	const books = join(build, 'books');
	if (!existsSync(books)) return found;
	for (const slug of readdirSync(books)) {
		const page = join(books, slug, 'index.html');
		if (!existsSync(page)) continue;
		for (const [, json] of readFileSync(page, 'utf8').matchAll(LD)) {
			try {
				const ld = JSON.parse(json);
				if (ld['@type'] !== 'Book' || !ld.image) continue;
				const file = join(build, new URL(ld.image).pathname);
				if (existsSync(file)) found.set(slug, file);
			} catch {
				/* not this block */
			}
		}
	}
	return found;
}

// ── Running ─────────────────────────────────────────────────────────────────

/**
 * Draw every job, eight at a time, into the build. `draw(job)` returns the
 * JPEG bytes; `job.dest` is the card's path in the build. A job that throws
 * gets the house card, and is listed. Eight in flight because Pango and the
 * encoder run on libvips' own threads — a slow card holds up only its worker.
 */
export async function drawAll(name, build, jobs, draw) {
	const started = Date.now();
	const failed = [];
	let next = 0;
	const one = async (job) => {
		const dest = join(build, job.dest);
		try {
			mkdirSync(dirname(dest), { recursive: true });
			writeFileSync(dest, await draw(job));
		} catch (err) {
			failed.push(`  ${job.label ?? job.dest} — ${err.message}`);
			await sharp(join(build, '/og/default.png'))
				.resize(W, H)
				.jpeg({ quality: 82 })
				.toFile(dest)
				.catch(() => {});
		}
	};
	await Promise.all(
		Array.from({ length: 8 }, async () => {
			while (next < jobs.length) await one(jobs[next++]);
		})
	);
	if (failed.length) {
		console.warn(`${name}: ${failed.length} page(s) got the default card:\n${failed.join('\n')}`);
	}
	console.log(
		`${name}: ${jobs.length - failed.length} cards, ${failed.length} fallbacks, ` +
			`in ${((Date.now() - started) / 1000).toFixed(1)}s`
	);
}

/** Run `main` when `url` is the script node was started with — and never let
 *  it fail the build: anything it misses, the pages still render. */
export async function runAsScript(url, name, main) {
	if (process.argv[1] && fileURLToPath(url) === resolve(process.argv[1])) {
		await main(resolve(process.cwd(), process.argv[2] ?? 'build')).catch((err) =>
			console.warn(`${name}: skipped — ${err.stack ?? err}`)
		);
	}
}
