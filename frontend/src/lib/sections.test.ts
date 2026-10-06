import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV } from './contentNav';
import { EMBLEM_ART } from './emblems';
import { SECTION_EMBLEMS } from './sectionEmblems';
import { SECTION_MARKS } from './sections';

const FLEURON = readFileSync(join(process.cwd(), 'src/lib/components/Fleuron.svelte'), 'utf-8');
const colours = (art: string) => new Set(art.match(/#[0-9a-f]{6}/gi)?.map((c) => c.toLowerCase()));

describe('section marks', () => {
	it('wear the icon the top nav gives each section', () => {
		for (const { section, icon } of PRIMARY_NAV) expect(SECTION_MARKS[section].icon, section).toBe(icon);
	});

	it('give each section its own ornament, and Fleuron draws every one', () => {
		const ornaments = Object.values(SECTION_MARKS).map((m) => m.ornament);
		expect(new Set(ornaments).size).toBe(ornaments.length);
		// A misspelt ornament would fall through to the house leaf silently.
		for (const o of ornaments) expect(FLEURON, `Fleuron draws no "${o}"`).toContain(`ornament === '${o}'`);
	});
});

describe('section emblems', () => {
	const palette = new Set(Object.values(EMBLEM_ART).flatMap((art) => [...colours(art)]));

	it('draw one per primary section', () => {
		expect(Object.keys(SECTION_EMBLEMS).sort()).toEqual(PRIMARY_NAV.map((d) => d.section).sort());
	});

	it('are their own art, never a catalogue emblem a topic or plan already wears', () => {
		const catalogue = new Set(Object.values(EMBLEM_ART).map((a) => a.replace(/\s+/g, '')));
		for (const [s, art] of Object.entries(SECTION_EMBLEMS)) expect(catalogue.has(art.replace(/\s+/g, '')), s).toBe(false);
	});

	it('are multicolour, in the emblems’ shared palette', () => {
		for (const [s, art] of Object.entries(SECTION_EMBLEMS)) {
			const used = colours(art);
			expect(used.size, `${s} uses ${used.size} colours`).toBeGreaterThanOrEqual(3);
			for (const c of used) expect(palette.has(c), `${s}: ${c} is not an emblem palette colour`).toBe(true);
		}
	});

	it('contain only inert drawing markup (rendered via {@html})', () => {
		for (const art of Object.values(SECTION_EMBLEMS))
			expect(art).not.toMatch(/<(script|foreignObject|use|image|a)\b|href|javascript:|\son\w+=/i);
	});
});
