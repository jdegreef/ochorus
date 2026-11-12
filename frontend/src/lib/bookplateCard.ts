// A bookplate as a PNG: the plate the finish panel shows, drawn on the cards'
// fixed paper so it can be saved, shared, or printed and pasted into a paper
// copy. Same paper, ink and gold as every card Ochorus draws (quoteCard.ts).
//
// hex-ok-file: the card's fixed palette (see quoteCard.ts) — it renders a PNG
// that leaves the site and has no theme to follow.

import type { CoverStyleId } from '$lib/coverStyles';
import { EX_LIBRIS, PLATE_FACES, isRtl, plateFilename, plateFontStack, textScripts } from '$lib/bookplate';
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

/** Load the faces the plate is lettered in — canvas does not wait for them. */
async function loadFaces(p: PlateText): Promise<void> {
	const face = PLATE_FACES[p.style];
	const all = [EX_LIBRIS, p.name, p.title].join(' ');
	await ensureFonts(cardScript(p.locale), [p.before, p.after, p.byline, p.date].join(' '));
	try {
		const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
		if (!fonts) return;
		await Promise.all([
			fonts.load(`${face.weight} 64px '${face.family}'`, all),
			...textScripts(all).map((s) => (SCRIPT_FACE[s] ? fonts.load(`400 64px '${SCRIPT_FACE[s]}'`, all) : null))
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

	// The owner's name: as large as it will go in two lines.
	const name = fit(ctx, p.name, faceFont, 104, 44, 2);
	ctx.font = faceFont(name.size);
	const nameLead = name.size * 1.2;
	let y = 560 - ((name.lines.length - 1) * nameLead) / 2;
	for (const l of name.lines) {
		line(ctx, l, y);
		y += nameLead;
	}

	// "finished <Title> by <Author>".
	const small = (px: number) => `400 ${px}px ${CARD_SERIF}`;
	y = 760;
	ctx.fillStyle = MUTED;
	if (p.before) {
		ctx.font = small(36);
		line(ctx, p.before, y);
		y += 70;
	}
	const title = fit(ctx, p.title, faceFont, 64, 34, 3);
	ctx.fillStyle = INK;
	ctx.font = faceFont(title.size);
	for (const l of title.lines) {
		line(ctx, l, y);
		y += title.size * 1.25;
	}
	ctx.fillStyle = MUTED;
	y += 18;
	if (p.after) {
		ctx.font = small(36);
		line(ctx, p.after, y);
		y += 56;
	}
	const by = fit(ctx, p.byline, small, 36, 26, 2);
	ctx.font = small(by.size);
	for (const l of by.lines) {
		line(ctx, l, y);
		y += by.size * 1.4;
	}

	// The date, then the house mark, small, at the foot.
	ctx.font = small(32);
	line(ctx, p.date, 1150);
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
