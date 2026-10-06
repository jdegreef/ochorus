/**
 * The home hero's scrim is tinted with the reader's palette (--hero-tint), not
 * black — so its contrast is measured, not trusted. The date line sits where
 * the scrim is 75% tint; the painting under it can be anything, so the worst
 * case is a white one. Every tint, composited at 75% over white, must still
 * carry --hero-ink at 4.5:1.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { contrastRatio } from './coverArt';
import { PALETTES } from './palettes';

const CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

function tintOf(selector: string): string | undefined {
	const start = CSS.indexOf(`${selector} {`);
	if (start === -1) return undefined;
	const body = CSS.slice(start, CSS.indexOf('}', start));
	return body.match(/--hero-tint:\s*(#[0-9a-f]{6});/i)?.[1];
}

const houseTint = CSS.match(/--hero-tint:\s*(#[0-9a-f]{6});/i)?.[1];
const ink = CSS.match(/--hero-ink:\s*(#[0-9a-f]{6});/i)?.[1];

describe('home hero tint', () => {
	it('declares the ink and the house tint', () => {
		expect(ink).toMatch(/^#[0-9a-f]{6}$/i);
		expect(houseTint).toMatch(/^#[0-9a-f]{6}$/i);
	});

	for (const p of PALETTES) {
		it(`${p}: the date line clears 4.5:1 over a white painting`, () => {
			const tint = p === 'parchment' ? houseTint : tintOf(`:root[data-palette='${p}']`);
			expect(tint, `${p} has no --hero-tint`).toMatch(/^#[0-9a-f]{6}$/i);
			const ground = rgb(tint!).map((c) => c * 0.75 + 255 * 0.25);
			expect(contrastRatio(rgb(ink!), ground)).toBeGreaterThanOrEqual(4.5);
		});
	}
});
