import { describe, expect, it } from 'vitest';
import { QR_MARGIN, qrMatrix, qrSvg } from './qr';

/** The path's dark modules back as a set of "row,col". */
function modules(path: string): Set<string> {
	const dark = new Set<string>();
	for (const [, c, r, w] of path.matchAll(/M(\d+) (\d+)h(\d+)v1h-\d+z/g))
		for (let i = 0; i < Number(w); i++) dark.add(`${r},${Number(c) + i}`);
	return dark;
}

describe('qrMatrix', () => {
	it('draws a square code with its three finder patterns', () => {
		const { size, path } = qrMatrix('https://ochorus.com/plans/new-to-the-faith/?together=2026-10-19&days=weekdays');
		expect(size).toBeGreaterThanOrEqual(21);
		expect((size - 17) % 4).toBe(0); // a QR side is 17 + 4 × version
		const dark = modules(path);
		// Each finder's top row: seven dark modules, at top-left, top-right, bottom-left.
		for (const [r, c] of [
			[0, 0],
			[0, size - 7],
			[size - 7, 0]
		])
			for (let i = 0; i < 7; i++) expect(dark.has(`${r},${c + i}`)).toBe(true);
	});

	it('merges a row’s run of dark modules into one rectangle', () => {
		// The finder's seven-module top edge is one run, not seven squares.
		expect(qrMatrix('x').path.startsWith('M0 0h7v1h-7z')).toBe(true);
	});

	it('grows with the text, and encodes non-ASCII as UTF-8 without throwing', () => {
		expect(qrMatrix('a'.repeat(200)).size).toBeGreaterThan(qrMatrix('a').size);
		expect(qrMatrix('Lisons ensemble : « Prière »').size).toBeGreaterThan(0);
	});
});

describe('qrSvg', () => {
	it('is a standalone black-on-white file with its quiet zone and an escaped title', () => {
		const svg = qrSvg('https://ochorus.com/', 'Read <together> & "share"');
		const { size } = qrMatrix('https://ochorus.com/');
		expect(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"')).toBe(true);
		expect(svg).toContain(`viewBox="-${QR_MARGIN} -${QR_MARGIN} ${size + 2 * QR_MARGIN} ${size + 2 * QR_MARGIN}"`);
		expect(svg).toContain('fill="white"');
		expect(svg).toContain('<title>Read &lt;together> &amp; &quot;share&quot;</title>');
	});
});
