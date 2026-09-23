// A testimony card: one answered prayer as a shareable image — what was prayed,
// how God answered, and how long it was prayed — on the same paper, type and
// footer as the quote card, so everything Ochorus sends out looks like one hand.
//
// hex-ok-file: the card's fixed palette (see quoteCard.ts) — it renders a PNG
// that leaves the site and has no theme to follow.

import { scriptOf } from '$lib/coverStyles';
import { daysWaited, type JournalEntry } from '$lib/journal';
import {
	CARD_SERIF,
	GOLD,
	INK,
	MUTED,
	SIZE,
	drawFooter,
	drawPaper,
	ensureFonts,
	fitQuote,
	quoteStyle,
	shareCardImage,
	trimQuote,
	wrapLines
} from '$lib/quoteCard';

/** Words the card sets, in the reader's language (the caller translates). */
export interface TestimonyLabels {
	/** "Answered prayer" — the card's heading. */
	heading: string;
	/** "We prayed" — above the request. */
	prayed: string;
	/** "God answered" — above the answer. */
	answered: string;
	/** "for {person}" when the person is included. */
	forPerson: (person: string) => string;
	/** "Prayed for 13 days · 20 September 2026". */
	meta: (days: number, answeredOn: string) => string;
}

export interface TestimonyOptions {
	/** Show what was asked. On by default: the answer means little without it. */
	includeRequest: boolean;
	/** Show who it was for. OFF by default — a name is someone else's story. */
	includePerson: boolean;
	locale: string;
	site?: string;
}

/** What the card will say — decided apart from the drawing, so it is tested. */
export interface TestimonyText {
	heading: string;
	request: string | null;
	answer: string;
	meta: string;
}

export function testimonyText(e: JournalEntry, o: TestimonyOptions, l: TestimonyLabels): TestimonyText {
	const asked = (e.title || e.body).trim();
	const who = o.includePerson && e.person ? ` ${l.forPerson(e.person)}` : '';
	const answeredOn = new Date(e.answeredAt ?? Date.now()).toLocaleDateString(o.locale, {
		day: 'numeric',
		month: 'long',
		year: 'numeric'
	});
	return {
		heading: l.heading,
		request: o.includeRequest && asked ? `${l.prayed}${who}: ${trimQuote(asked, 180)}` : null,
		// An answered prayer with no words of answer still testifies: say so.
		answer: trimQuote(e.answer || l.answered, 240),
		meta: l.meta(daysWaited(e) ?? 0, answeredOn)
	};
}

/** Draw the card to a PNG. */
export async function renderTestimonyCard(text: TestimonyText, answeredLabel: string, o: TestimonyOptions): Promise<Blob> {
	const script = scriptOf(o.locale);
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
	ctx.textBaseline = 'top';
	ctx.textAlign = 'left';

	// Heading, like a stamp: small capitals in the answered green.
	ctx.fillStyle = '#3b6d11';
	ctx.font = `700 26px ${CARD_SERIF}`;
	ctx.fillText(`✓  ${text.heading.toLocaleUpperCase(o.locale)}`, margin, 118);

	let y = 176;
	if (text.request) {
		ctx.fillStyle = MUTED;
		ctx.font = `400 32px ${CARD_SERIF}`;
		const lines = wrapLines(ctx, text.request, maxWidth).slice(0, 4);
		for (const line of lines) {
			ctx.fillText(line, margin, y);
			y += 44;
		}
		y += 26;
	}

	// "God answered", then the answer itself — the card's voice. Label and
	// answer are one block, set in the middle of the space left, so a short
	// answer does not sit under its label above an empty page.
	const bottom = 842;
	const labelGap = 52;
	const { lines, fontSize, lineHeight } = fitQuote(ctx, text.answer, maxWidth, bottom - y - labelGap, style, 64, 30);
	y += Math.max(0, (bottom - y - labelGap - lines.length * lineHeight) / 2);
	ctx.fillStyle = GOLD;
	ctx.font = `600 30px ${CARD_SERIF}`;
	ctx.fillText(answeredLabel, margin, y);
	y += labelGap;
	ctx.fillStyle = INK;
	ctx.font = `${style} ${fontSize}px ${CARD_SERIF}`;
	for (const line of lines) {
		ctx.fillText(line, margin, y);
		y += lineHeight;
	}

	ctx.fillStyle = MUTED;
	ctx.font = `400 26px ${CARD_SERIF}`;
	ctx.fillText(text.meta, margin, 884);

	drawFooter(ctx, margin, o.site);

	return await new Promise<Blob>((resolve, reject) => {
		canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png');
	});
}

export async function shareTestimonyCard(blob: Blob, text: TestimonyText): Promise<'shared' | 'downloaded'> {
	return shareCardImage(blob, 'ochorus-answered-prayer.png', `${text.heading}: ${text.answer}`);
}
