/**
 * The library sections' marks — /marks/emblem-<section>.svg beside a section's
 * page title, /marks/ornament-<name>.svg under it (PRIMARY_NAV names both).
 * Static files, so these check what a type can't: that every file a section
 * names exists, and that the emblems are drawn like the topic and plan art.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV } from './contentNav';
import { EMBLEM_ART } from './emblems';

const MARKS = join(process.cwd(), 'static/marks');
const read = (file: string) => readFileSync(join(MARKS, file), 'utf-8');
const colours = (art: string) => new Set(art.match(/#[0-9a-f]{6}/gi)?.map((c) => c.toLowerCase()));
const INERT = /<(script|foreignObject|image|a)\b|javascript:|\son\w+=/i;

describe('section ornaments', () => {
	it('has a file for every section, and no two sections share one', () => {
		const ornaments = PRIMARY_NAV.map((d) => d.ornament);
		expect(new Set(ornaments).size).toBe(ornaments.length);
		for (const o of ornaments) expect(existsSync(join(MARKS, `ornament-${o}.svg`)), `ornament-${o}.svg`).toBe(true);
	});

	it('are single-ink line art (a CSS mask paints them gold), and inert', () => {
		for (const { ornament } of PRIMARY_NAV) {
			const svg = read(`ornament-${ornament}.svg`);
			expect(svg).not.toMatch(INERT);
			// Black strokes and nothing else: any other ink would show through the
			// mask as the same gold, so a second colour means a drawing mistake.
			expect(svg, ornament).toContain('stroke="#000"');
			expect(colours(svg).size, ornament).toBe(0);
			expect(svg, ornament).not.toMatch(/\bfill="(?!none)/);
		}
	});
});

describe('section emblems', () => {
	const palette = new Set(Object.values(EMBLEM_ART).flatMap((art) => [...colours(art)]));

	it('has a file for every section', () => {
		for (const { section } of PRIMARY_NAV)
			expect(existsSync(join(MARKS, `emblem-${section}.svg`)), `emblem-${section}.svg`).toBe(true);
	});

	it('are multicolour, in the topic and plan emblems’ palette, and inert', () => {
		for (const { section } of PRIMARY_NAV) {
			const svg = read(`emblem-${section}.svg`);
			const used = colours(svg);
			expect(svg).not.toMatch(INERT);
			expect(used.size, `${section} uses ${used.size} colours`).toBeGreaterThanOrEqual(3);
			for (const c of used) expect(palette.has(c), `${section}: ${c} is not an emblem palette colour`).toBe(true);
		}
	});

	it('are their own art, never a catalogue emblem a topic or plan already wears', () => {
		const catalogue = Object.values(EMBLEM_ART).map((a) => a.replace(/\s+/g, ''));
		for (const { section } of PRIMARY_NAV) {
			const inner = read(`emblem-${section}.svg`).replace(/<\/?svg[^>]*>/g, '').replace(/\s+/g, '');
			expect(catalogue.some((a) => a === inner), section).toBe(false);
		}
	});
});
