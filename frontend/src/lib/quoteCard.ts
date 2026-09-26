// Render a selected quote into a branded, shareable PNG — a sermon or chapter
// line is the most shareable unit in the whole library, so this turns one into
// organic reach. Pure canvas (no external libs); the palette is a deliberate
// "paper" look, fixed regardless of the viewer's theme so a shared image reads
// the same everywhere.
//
// hex-ok-file: that fixed palette is the whole point. This renders a PNG that
// leaves the site — it has no theme to follow, and a card shared from lamplight
// must look identical to one shared from paper.

import markSvg from '$lib/brand/ochorus-mark.svg?raw';

import { scriptOf } from '$lib/coverStyles';

export interface QuoteCardOptions {
	quote: string;
	author: string;
	/** Where it's from, e.g. "Humility, Chapter 1" — shown under the author. */
	source: string;
	/** Footer site label, e.g. "ochorus.com". */
	site?: string;
	/** The edition's language, so the card can be set in the reader's script.
	 *  Optional, and Latin when absent — a caller that does not know is no worse
	 *  off than before, rather than broken. */
	language?: string;
}

/**
 * The serif stack, as a canvas literal.
 *
 * A LITERAL BECAUSE CANVAS CANNOT READ A CUSTOM PROPERTY. Everywhere else in
 * the app this list is `var(--font-display)` and there is one copy; `ctx.font`
 * takes a plain font shorthand, so this is the one place that genuinely has to
 * restate it. `quoteCard.test.ts` checks it against app.css so the copy cannot
 * drift.
 *
 * It matters here for the same reason it matters in the reader: this card draws
 * the reader's OWN SENTENCE, and it was set in `'Fraunces Variable', Georgia,
 * serif` — neither of which has an Arabic or Devanagari glyph. An Arabic reader
 * highlighting a line and tapping "Quote card" got a PNG in whatever serif the
 * device chose, on the one surface built to leave the site.
 */
export const CARD_SERIF =
	"'Fraunces Variable', 'Amiri', 'Tiro Devanagari Hindi', 'Noto Serif Ethiopic', 'PT Serif', Georgia, 'Times New Roman', serif";

/**
 * How the quote itself is set, per script.
 *
 * UPRIGHT AND 400 OUTSIDE LATIN, where the Latin card is `italic 600`. Not
 * taste: Amiri and Tiro have no italic at all and Amiri ships 400 and 700 with
 * nothing between, so `italic 600` asked all three faces for two things they
 * have not got and got a synthesised slant over a synthesised bold. An upright
 * pull-quote is right in each of these traditions anyway.
 */
export const quoteStyle = (script: string | null) => (script ? '400' : 'italic 600');

// The card's fixed paper palette and size — shared by every card Ochorus draws
// (the quote card here, the testimony card in testimonyCard.ts).
export const SIZE = 1080;
export const PAPER = '#f7f1e5';
export const INK = '#221c15';
export const MUTED = '#6e6358';
export const GOLD = '#b07d22';

// Keep a card legible: an over-long selection is trimmed at a word boundary.
const MAX_CHARS = 300;

export function trimQuote(q: string, max = MAX_CHARS): string {
	const s = q.replace(/\s+/g, ' ').trim();
	if (s.length <= max) return s;
	const cut = s.slice(0, max);
	const lastSpace = cut.lastIndexOf(' ');
	return (lastSpace > 0 ? cut.slice(0, lastSpace) : cut).replace(/[,;:.\s]+$/, '') + '…';
}

/** Greedy word-wrap for the current ctx.font. */
export function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
	const words = text.split(' ');
	const lines: string[] = [];
	let line = '';
	for (const w of words) {
		const trial = line ? `${line} ${w}` : w;
		if (ctx.measureText(trial).width > maxWidth && line) {
			lines.push(line);
			line = w;
		} else {
			line = trial;
		}
	}
	if (line) lines.push(line);
	return lines;
}

/** Pick the largest quote font size whose wrapped lines fit the target box. */
export function fitQuote(
	ctx: CanvasRenderingContext2D,
	text: string,
	maxWidth: number,
	maxHeight: number,
	style: string,
	largest = 70,
	smallest = 30
): { lines: string[]; fontSize: number; lineHeight: number } {
	for (let fs = largest; fs >= smallest; fs -= 2) {
		ctx.font = `${style} ${fs}px ${CARD_SERIF}`;
		const lines = wrapLines(ctx, text, maxWidth);
		const lineHeight = fs * 1.34;
		if (lines.length * lineHeight <= maxHeight) return { lines, fontSize: fs, lineHeight };
	}
	ctx.font = `${style} ${smallest}px ${CARD_SERIF}`;
	return { lines: wrapLines(ctx, text, maxWidth), fontSize: smallest, lineHeight: smallest * 1.34 };
}

/**
 * The Ochorus mark, from the real artwork.
 *
 * This was the THIRD hand-drawn copy of the logo — 24×24 stroke paths captioned
 * "from BrandMark.svelte", carrying the same wrong-way quill as the other two,
 * and left behind when those were replaced. Quote cards are shared publicly, so
 * it was the retired mark that went out on them.
 *
 * The artwork is fills, not strokes, so this fills; and its viewBox is
 * normalised to `0 0 w h`, so fitting it into a box is one uniform scale.
 */
const markPath = (() => {
	let cached: { path: Path2D; vw: number; vh: number } | null = null;
	return (size: number) => {
		if (!cached) {
			const [, vw, vh] = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(markSvg)!.map(Number);
			const path = new Path2D();
			for (const [, d] of markSvg.matchAll(/ d="([^"]+)"/g)) path.addPath(new Path2D(d));
			cached = { path, vw, vh };
		}
		const k = size / Math.max(cached.vw, cached.vh);
		const fitted = new Path2D();
		fitted.addPath(cached.path, new DOMMatrix().scale(k));
		return fitted;
	};
})();

export function drawMark(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, color: string) {
	ctx.save();
	ctx.translate(x, y);
	ctx.fillStyle = color;
	ctx.fill(markPath(size));
	ctx.restore();
}

/** The face each script's quote is actually drawn in — what has to be LOADED
 *  before the canvas paints, since `ctx.fillText` does not wait for a webfont
 *  the way the DOM does: it silently falls back and the PNG keeps the fallback
 *  forever. Mirrors the non-Latin families in `SERIF`. */
export const SCRIPT_FACE: Record<string, string> = {
	arabic: 'Amiri',
	devanagari: 'Tiro Devanagari Hindi',
	cyrillic: 'PT Serif',
	ethiopic: 'Noto Serif Ethiopic'
};

export async function ensureFonts(script: string | null): Promise<void> {
	try {
		const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
		if (!fonts) return;
		const face = script && SCRIPT_FACE[script];
		await Promise.all([
			fonts.load("italic 600 64px 'Fraunces Variable'"),
			fonts.load("600 40px 'Fraunces Variable'"),
			// The script face at both sizes the card sets it at. Without this the
			// card drew Arabic in the device serif even though the stack named
			// Amiri, because nothing had asked the browser to fetch it yet.
			...(face ? [fonts.load(`400 64px '${face}'`), fonts.load(`600 34px '${face}'`)] : [])
		]);
		await fonts.ready;
	} catch {
		/* fall back to Georgia — still a serif, still legible */
	}
}

/** The card's paper, and a hairline frame inset from its edge. */
export function drawPaper(ctx: CanvasRenderingContext2D) {
	ctx.fillStyle = PAPER;
	ctx.fillRect(0, 0, SIZE, SIZE);
	ctx.strokeStyle = 'rgba(34,28,21,0.14)';
	ctx.lineWidth = 2;
	ctx.strokeRect(48.5, 48.5, SIZE - 97, SIZE - 97);
}

/** The card's foot: a gold rule, the mark and wordmark, and the site. */
export function drawFooter(ctx: CanvasRenderingContext2D, margin: number, site?: string) {
	const footY = 946;
	ctx.strokeStyle = 'rgba(176,125,34,0.5)';
	ctx.lineWidth = 1.5;
	ctx.beginPath();
	ctx.moveTo(margin, footY);
	ctx.lineTo(SIZE - margin, footY);
	ctx.stroke();

	drawMark(ctx, margin, footY + 16, 40, INK);
	ctx.fillStyle = INK;
	ctx.font = `700 30px ${CARD_SERIF}`;
	ctx.textBaseline = 'alphabetic';
	ctx.fillText('Ochorus', margin + 54, footY + 47);

	if (site) {
		ctx.fillStyle = MUTED;
		ctx.font = '400 26px Georgia, serif';
		ctx.textAlign = 'right';
		ctx.fillText(site, SIZE - margin, footY + 47);
		ctx.textAlign = 'left';
	}
}

/** Render the card to a PNG Blob. */
export async function renderQuoteCard(opts: QuoteCardOptions): Promise<Blob> {
	const script = scriptOf(opts.language ?? 'en');
	const style = quoteStyle(script);
	await ensureFonts(script);
	const canvas = document.createElement('canvas');
	canvas.width = SIZE;
	canvas.height = SIZE;
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('canvas 2d unavailable');

	drawPaper(ctx);

	const margin = 132;
	const maxWidth = SIZE - margin * 2;

	// Opening quotation glyph.
	ctx.fillStyle = GOLD;
	ctx.font = "700 190px Georgia, 'Times New Roman', serif";
	ctx.textBaseline = 'alphabetic';
	ctx.textAlign = 'left';
	ctx.fillText('“', margin - 6, 268);

	// Quote text, auto-fit and vertically centred in the body region.
	const quote = trimQuote(opts.quote);
	const bodyTop = 300;
	const bodyBottom = 812;
	const { lines, fontSize, lineHeight } = fitQuote(ctx, quote, maxWidth, bodyBottom - bodyTop, style);
	ctx.fillStyle = INK;
	ctx.font = `${style} ${fontSize}px ${CARD_SERIF}`;
	ctx.textBaseline = 'top';
	const blockHeight = lines.length * lineHeight;
	let y = bodyTop + Math.max(0, (bodyBottom - bodyTop - blockHeight) / 2);
	for (const line of lines) {
		ctx.fillText(line, margin, y);
		y += lineHeight;
	}

	// Attribution.
	ctx.fillStyle = INK;
	ctx.font = `600 34px ${CARD_SERIF}`;
	ctx.fillText(`— ${opts.author}`, margin, 864);
	if (opts.source) {
		ctx.fillStyle = MUTED;
		// The source is a BOOK TITLE, so it is translated — Georgia alone has no
		// Devanagari, and this line was the last one still naming it.
		ctx.font = `400 26px ${CARD_SERIF}`;
		ctx.fillText(opts.source, margin, 910);
	}

	drawFooter(ctx, margin, opts.site);

	return await new Promise<Blob>((resolve, reject) => {
		canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png');
	});
}

/**
 * Produce the card and hand it off: the native share sheet with the image file
 * where supported (mobile), otherwise a PNG download. Returns 'shared' |
 * 'downloaded' so the caller can reflect what happened.
 */
export async function shareQuoteCard(opts: QuoteCardOptions): Promise<'shared' | 'downloaded'> {
	const blob = await renderQuoteCard(opts);
	return shareCardImage(blob, 'ochorus-quote.png', `"${trimQuote(opts.quote)}" — ${opts.author}`);
}

/**
 * Hand a rendered card off: the native share sheet with the image file where
 * supported (mobile), otherwise a PNG download. Returns 'shared' |
 * 'downloaded' so the caller can reflect what happened.
 */
export async function shareCardImage(blob: Blob, filename: string, text: string): Promise<'shared' | 'downloaded'> {
	const file = new File([blob], filename, { type: 'image/png' });
	const nav = navigator as Navigator & {
		canShare?: (data?: ShareData) => boolean;
	};
	if (nav.canShare && nav.canShare({ files: [file] })) {
		try {
			await navigator.share({ files: [file], text });
			return 'shared';
		} catch {
			/* user dismissed, or share failed — fall through to download */
		}
	}
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
	return 'downloaded';
}
