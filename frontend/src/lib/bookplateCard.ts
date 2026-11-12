// A bookplate as a PNG: the plate the finish panel shows, drawn on the cards'
// fixed paper so it can be saved, shared, or printed and pasted into a paper
// copy. Same paper, ink and gold as every card Ochorus draws (quoteCard.ts).
//
// hex-ok-file: the card's fixed palette (see quoteCard.ts) — it renders a PNG
// that leaves the site and has no theme to follow.

import type { CoverStyleId } from '$lib/coverStyles';
import {
	EX_LIBRIS,
	PLATE_FACES,
	SANS_SCRIPT_FACE,
	isRtl,
	plateFilename,
	plateFontStack,
	textScripts
} from '$lib/bookplate';
import {
	CARD_SERIF,
	GOLD,
	INK,
	MUTED,
	PAPER,
	SCRIPT_FACE,
	cardScript,
	drawMark,
	ensureFonts,
	shareCardImage,
	wrapLines,
	type CardShareResult
} from '$lib/quoteCard';

/** What the plate says, already translated and formatted by the caller. */
export interface PlateText {
	slug: string;
	name: string;
	/** The words around the title: "finished" / "" (from `splitAround`). */
	before: string;
	title: string;
	after: string;
	/** "by C. H. Spurgeon". */
	byline: string;
	date: string;
	style: CoverStyleId;
	/** The reader's locale — the date's and the connecting words' script. */
	locale: string;
}

const W = 1080;
const H = 1350;
const CX = W / 2;
const TEXT_W = 760;

/** The band between the ornament and the date that the name and the words
 *  share; the date sits on a fixed line below it. */
const BAND_TOP = 430;
const BAND_BOTTOM = 1080;
const DATE_Y = 1150;

/** The house leaf (Fleuron.svelte's), between two hairlines. */
function drawOrnament(ctx: CanvasRenderingContext2D, y: number) {
	ctx.save();
	ctx.strokeStyle = GOLD;
	ctx.lineWidth = 2;
	ctx.lineCap = 'round';
	ctx.beginPath();
	ctx.moveTo(CX - 150, y);
	ctx.lineTo(CX - 34, y);
	ctx.moveTo(CX + 34, y);
	ctx.lineTo(CX + 150, y);
	ctx.stroke();
	ctx.translate(CX - 24, y - 24);
	ctx.scale(2, 2);
	ctx.lineWidth = 1.3;
	ctx.stroke(new Path2D('M12 2.5c-4.5 4.5-4.5 14.5 0 19 4.5-4.5 4.5-14.5 0-19z'));
	ctx.stroke(new Path2D('M12 6v12'));
	ctx.restore();
}

/** Largest size (step 2) at which `text` wraps into `maxLines` within the width. */
function fit(
	ctx: CanvasRenderingContext2D,
	text: string,
	font: (px: number) => string,
	largest: number,
	smallest: number,
	maxLines: number
): { lines: string[]; size: number } {
	for (let px = largest; px >= smallest; px -= 2) {
		ctx.font = font(px);
		const lines = wrapLines(ctx, text, TEXT_W);
		if (lines.length <= maxLines) return { lines, size: px };
	}
	ctx.font = font(smallest);
	const lines = wrapLines(ctx, text, TEXT_W);
	// Still too long at the smallest size: keep what fits and mark the cut.
	if (lines.length > maxLines) {
		lines.length = maxLines;
		lines[maxLines - 1] = `${lines[maxLines - 1].replace(/[\s,;:.]+$/, '')}…`;
	}
	return { lines, size: smallest };
}

function line(ctx: CanvasRenderingContext2D, text: string, y: number) {
	ctx.direction = isRtl(text) ? 'rtl' : 'ltr';
	ctx.fillText(text, CX, y);
}

/** A run of centred lines in one font, measured by its ink: how far its first
 *  line climbs above the baseline and its last falls below. */
interface Block {
	lines: string[];
	font: string;
	color: string;
	/** Baseline to baseline. */
	lead: number;
	/** Space to the block after it. */
	gap: number;
	ascent: number;
	descent: number;
}

function block(
	ctx: CanvasRenderingContext2D,
	lines: string[],
	px: number,
	font: string,
	color: string,
	lead: number,
	gap: number
): Block {
	ctx.font = font;
	const first = ctx.measureText(lines[0] ?? '');
	const last = ctx.measureText(lines[lines.length - 1] ?? '');
	// At least a Latin cap and descender, so a line of x-height letters keeps
	// the same air as one with capitals; more when the ink takes more. Arabic in
	// Amiri climbs and falls far further than Latin at one size, and the fixed
	// slots this replaced pushed a two-line Arabic name into the ornament.
	return {
		lines,
		font,
		color,
		lead,
		gap,
		ascent: Math.max(first.actualBoundingBoxAscent || 0, px * 0.72),
		descent: Math.max(last.actualBoundingBoxDescent || 0, px * 0.22)
	};
}

const blockHeight = (b: Block) => b.ascent + (b.lines.length - 1) * b.lead + b.descent;
const stackHeight = (blocks: Block[]) =>
	blocks.reduce((h, b, i) => h + blockHeight(b) + (i < blocks.length - 1 ? b.gap : 0), 0);

/** The smallest size a name is set at on two lines before it may take a third. */
const NAME_TWO_LINES_MIN = 56;

/**
 * The owner's name: on one or two lines while it can stay at a plate's size,
 * and only then on three, smaller — so a long name is set whole rather than
 * cut at two lines with an ellipsis (the display name holds up to 120
 * characters, which three lines at the smallest size carry).
 */
function fitName(
	ctx: CanvasRenderingContext2D,
	name: string,
	font: (px: number) => string,
	largest: number
): { lines: string[]; size: number } {
	ctx.font = font(NAME_TWO_LINES_MIN);
	if (largest > NAME_TWO_LINES_MIN && wrapLines(ctx, name, TEXT_W).length <= 2) {
		return fit(ctx, name, font, largest, NAME_TWO_LINES_MIN, 2);
	}
	return fit(ctx, name, font, Math.min(largest, NAME_TWO_LINES_MIN), 40, 3);
}

/**
 * The name, then "finished <Title> by <Author>", as measured blocks — the big
 * sizes stepped down together until the whole stack fits the band. Each used to
 * sit at a fixed y, so a three-line title over a two-line byline ran into the
 * date, and a two-line Arabic name rose into the ornament.
 */
function layout(ctx: CanvasRenderingContext2D, p: PlateText, faceFont: (px: number) => string): Block[] {
	const small = (px: number) => `400 ${px}px ${CARD_SERIF}`;
	let blocks: Block[] = [];
	for (let step = 0; step <= 8; step++) {
		const name = fitName(ctx, p.name, faceFont, 104 - step * 8);
		const title = fit(ctx, p.title, faceFont, 64 - step * 4, 32, 3);
		const wordsPx = Math.max(36 - step * 2, 28);
		const by = fit(ctx, p.byline, small, wordsPx, 26, 2);
		blocks = [
			block(ctx, name.lines, name.size, faceFont(name.size), INK, name.size * 1.2, 96),
			...(p.before ? [block(ctx, [p.before], wordsPx, small(wordsPx), MUTED, 0, 24)] : []),
			block(ctx, title.lines, title.size, faceFont(title.size), INK, title.size * 1.25, 30),
			...(p.after ? [block(ctx, [p.after], wordsPx, small(wordsPx), MUTED, 0, 24)] : []),
			block(ctx, by.lines, by.size, small(by.size), MUTED, by.size * 1.4, 0)
		];
		if (stackHeight(blocks) <= BAND_BOTTOM - BAND_TOP) break;
	}
	return blocks;
}

/** Load the faces the plate is lettered in — canvas does not wait for them. */
async function loadFaces(p: PlateText): Promise<void> {
	const face = PLATE_FACES[p.style];
	// The young-reader plate is sans: loading Amiri for it left its Arabic in
	// the device font. The serif stack's faces are the cards' own.
	const scriptFace: Record<string, string> = p.style === 'young' ? SANS_SCRIPT_FACE : SCRIPT_FACE;
	const all = [EX_LIBRIS, p.name, p.title].join(' ');
	await ensureFonts(cardScript(p.locale), [p.before, p.after, p.byline, p.date].join(' '));
	try {
		const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
		if (!fonts) return;
		// At the weight the plate is drawn at: Amiri ships 400 and 700, so a 600
		// plate matched the 700 face, which a load at 400 never fetched.
		await Promise.all([
			fonts.load(`${face.weight} 64px '${face.family}'`, all),
			...textScripts(all).map((s) =>
				scriptFace[s] ? fonts.load(`${face.weight} 64px '${scriptFace[s]}'`, all) : null
			)
		]);
	} catch {
		/* a fallback serif is still a plate */
	}
}

/** Draw the plate to a PNG. */
export async function renderBookplate(p: PlateText): Promise<Blob> {
	await loadFaces(p);
	const canvas = document.createElement('canvas');
	canvas.width = W;
	canvas.height = H;
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('canvas 2d unavailable');

	// Paper, and the plate's double rule: a heavy line in ink, a fine one in gold.
	ctx.fillStyle = PAPER;
	ctx.fillRect(0, 0, W, H);
	ctx.strokeStyle = INK;
	ctx.lineWidth = 4;
	ctx.strokeRect(70, 70, W - 140, H - 140);
	ctx.strokeStyle = GOLD;
	ctx.lineWidth = 1.5;
	ctx.strokeRect(88, 88, W - 176, H - 176);

	const face = PLATE_FACES[p.style];
	const stack = plateFontStack(p.style);
	const faceFont = (px: number) => `${face.weight} ${px}px ${stack}`;
	ctx.textAlign = 'center';
	ctx.textBaseline = 'alphabetic';

	// EX LIBRIS, tracked like a cut inscription.
	ctx.fillStyle = INK;
	ctx.font = faceFont(84);
	(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '8px';
	line(ctx, EX_LIBRIS, 290);
	(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '0px';

	drawOrnament(ctx, 370);

	// The name and the words, centred together in the band — a little above
	// its middle, where the eye sets a plate's name.
	const blocks = layout(ctx, p, faceFont);
	let top = BAND_TOP + Math.max(0, (BAND_BOTTOM - BAND_TOP - stackHeight(blocks)) * 0.42);
	for (const b of blocks) {
		ctx.font = b.font;
		ctx.fillStyle = b.color;
		let y = top + b.ascent;
		for (const l of b.lines) {
			line(ctx, l, y);
			y += b.lead;
		}
		top += blockHeight(b) + b.gap;
	}

	// The date, then the house mark, small, at the foot.
	ctx.fillStyle = MUTED;
	ctx.font = `400 32px ${CARD_SERIF}`;
	line(ctx, p.date, DATE_Y);
	drawMark(ctx, CX - 18, 1188, 36, GOLD);

	return await new Promise<Blob>((resolve, reject) => {
		canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png');
	});
}

/** Draw the plate and hand it off: the share sheet, or a download. */
export async function saveBookplate(p: PlateText): Promise<CardShareResult> {
	const blob = await renderBookplate(p);
	return shareCardImage(blob, plateFilename(p.slug), `${EX_LIBRIS} · ${p.name} · ${p.title}`);
}
