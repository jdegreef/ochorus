// Render a selected quote into a branded, shareable PNG — a sermon or chapter
// line is the most shareable unit in the whole library, so this turns one into
// organic reach. Pure canvas (no external libs); the palette is a deliberate
// "paper" look, fixed regardless of the viewer's theme so a shared image reads
// the same everywhere.

import markSvg from '$lib/brand/ochorus-mark.svg?raw';

export interface QuoteCardOptions {
	quote: string;
	author: string;
	/** Where it's from, e.g. "Humility, Chapter 1" — shown under the author. */
	source: string;
	/** Footer site label, e.g. "ochorus.com". */
	site?: string;
}

const SIZE = 1080;
const PAPER = '#f7f1e5';
const INK = '#221c15';
const MUTED = '#6e6358';
const GOLD = '#b07d22';

// Keep a card legible: an over-long selection is trimmed at a word boundary.
const MAX_CHARS = 300;

function trimQuote(q: string): string {
	const s = q.replace(/\s+/g, ' ').trim();
	if (s.length <= MAX_CHARS) return s;
	const cut = s.slice(0, MAX_CHARS);
	const lastSpace = cut.lastIndexOf(' ');
	return (lastSpace > 0 ? cut.slice(0, lastSpace) : cut).replace(/[,;:.\s]+$/, '') + '…';
}

/** Greedy word-wrap for the current ctx.font. */
function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
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
function fitQuote(
	ctx: CanvasRenderingContext2D,
	text: string,
	maxWidth: number,
	maxHeight: number
): { lines: string[]; fontSize: number; lineHeight: number } {
	for (let fs = 70; fs >= 30; fs -= 2) {
		ctx.font = `italic 600 ${fs}px 'Fraunces Variable', Georgia, serif`;
		const lines = wrapLines(ctx, text, maxWidth);
		const lineHeight = fs * 1.34;
		if (lines.length * lineHeight <= maxHeight) return { lines, fontSize: fs, lineHeight };
	}
	ctx.font = `italic 600 30px 'Fraunces Variable', Georgia, serif`;
	return { lines: wrapLines(ctx, text, maxWidth), fontSize: 30, lineHeight: 30 * 1.34 };
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

function drawMark(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, color: string) {
	ctx.save();
	ctx.translate(x, y);
	ctx.fillStyle = color;
	ctx.fill(markPath(size));
	ctx.restore();
}

async function ensureFonts(): Promise<void> {
	try {
		const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
		if (!fonts) return;
		await Promise.all([
			fonts.load("italic 600 64px 'Fraunces Variable'"),
			fonts.load("600 40px 'Fraunces Variable'")
		]);
		await fonts.ready;
	} catch {
		/* fall back to Georgia — still a serif, still legible */
	}
}

/** Render the card to a PNG Blob. */
export async function renderQuoteCard(opts: QuoteCardOptions): Promise<Blob> {
	await ensureFonts();
	const canvas = document.createElement('canvas');
	canvas.width = SIZE;
	canvas.height = SIZE;
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('canvas 2d unavailable');

	// Background + inset frame.
	ctx.fillStyle = PAPER;
	ctx.fillRect(0, 0, SIZE, SIZE);
	ctx.strokeStyle = 'rgba(34,28,21,0.14)';
	ctx.lineWidth = 2;
	ctx.strokeRect(48.5, 48.5, SIZE - 97, SIZE - 97);

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
	const { lines, fontSize, lineHeight } = fitQuote(ctx, quote, maxWidth, bodyBottom - bodyTop);
	ctx.fillStyle = INK;
	ctx.font = `italic 600 ${fontSize}px 'Fraunces Variable', Georgia, serif`;
	ctx.textBaseline = 'top';
	const blockHeight = lines.length * lineHeight;
	let y = bodyTop + Math.max(0, (bodyBottom - bodyTop - blockHeight) / 2);
	for (const line of lines) {
		ctx.fillText(line, margin, y);
		y += lineHeight;
	}

	// Attribution.
	ctx.fillStyle = INK;
	ctx.font = "600 34px 'Fraunces Variable', Georgia, serif";
	ctx.fillText(`— ${opts.author}`, margin, 864);
	if (opts.source) {
		ctx.fillStyle = MUTED;
		ctx.font = '400 26px Georgia, serif';
		ctx.fillText(opts.source, margin, 910);
	}

	// Footer: gold rule, mark + wordmark on the left, site on the right.
	const footY = 946;
	ctx.strokeStyle = 'rgba(176,125,34,0.5)';
	ctx.lineWidth = 1.5;
	ctx.beginPath();
	ctx.moveTo(margin, footY);
	ctx.lineTo(SIZE - margin, footY);
	ctx.stroke();

	drawMark(ctx, margin, footY + 16, 40, INK);
	ctx.fillStyle = INK;
	ctx.font = "700 30px 'Fraunces Variable', Georgia, serif";
	ctx.textBaseline = 'alphabetic';
	ctx.fillText('Ochorus', margin + 54, footY + 47);

	if (opts.site) {
		ctx.fillStyle = MUTED;
		ctx.font = '400 26px Georgia, serif';
		ctx.textAlign = 'right';
		ctx.fillText(opts.site, SIZE - margin, footY + 47);
		ctx.textAlign = 'left';
	}

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
	const file = new File([blob], 'ochorus-quote.png', { type: 'image/png' });
	const nav = navigator as Navigator & {
		canShare?: (data?: ShareData) => boolean;
	};
	if (nav.canShare && nav.canShare({ files: [file] })) {
		try {
			await navigator.share({
				files: [file],
				text: `"${trimQuote(opts.quote)}" — ${opts.author}`
			});
			return 'shared';
		} catch {
			/* user dismissed, or share failed — fall through to download */
		}
	}
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'ochorus-quote.png';
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
	return 'downloaded';
}
