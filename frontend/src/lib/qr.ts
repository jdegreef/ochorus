import qrcode from 'qrcode-generator';

/**
 * A link as a QR code — for the projector slide, the poster and the bulletin
 * insert, where a room full of phones can't tap a link. Drawn as one SVG path
 * (each row's run of dark modules a rectangle), so it is crisp at any size,
 * prints as vector, and renders in the prerendered HTML with no canvas. Pure,
 * so the encoding is tested apart from the page.
 *
 * Error correction M: a link read off paper or a screen across a room, where
 * a little damage or glare must not cost the scan, yet the code stays small
 * enough to read at bulletin size.
 */

/** The quiet zone the spec asks for around the code, in modules. */
export const QR_MARGIN = 4;

export interface QrMatrix {
	/** Modules per side, quiet zone excluded. */
	size: number;
	/** An SVG path in module units: every dark module, row runs merged. */
	path: string;
}

export function qrMatrix(text: string): QrMatrix {
	const qr = qrcode(0, 'M');
	// The library keeps only each char's low byte, so hand it the UTF-8 bytes:
	// a French message may carry an accented character.
	qr.addData(String.fromCharCode(...new TextEncoder().encode(text)), 'Byte');
	qr.make();
	const size = qr.getModuleCount();
	const runs: string[] = [];
	for (let r = 0; r < size; r++) {
		let c = 0;
		while (c < size) {
			if (!qr.isDark(r, c)) {
				c++;
				continue;
			}
			const from = c;
			while (c < size && qr.isDark(r, c)) c++;
			runs.push(`M${from} ${r}h${c - from}v1h-${c - from}z`);
		}
	}
	return { size, path: runs.join('') };
}

/** The code as a standalone SVG file — black on white with its quiet zone, to
 *  drop into a slide, a newsletter or a print shop's layout. */
export function qrSvg(text: string, title: string): string {
	const { size, path } = qrMatrix(text);
	const box = size + QR_MARGIN * 2;
	const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
	return (
		`<svg xmlns="http://www.w3.org/2000/svg" viewBox="-${QR_MARGIN} -${QR_MARGIN} ${box} ${box}" width="${box * 10}" height="${box * 10}" shape-rendering="crispEdges">` +
		`<title>${esc(title)}</title>` +
		`<rect x="-${QR_MARGIN}" y="-${QR_MARGIN}" width="${box}" height="${box}" fill="white"/>` +
		`<path d="${path}" fill="black"/></svg>`
	);
}
