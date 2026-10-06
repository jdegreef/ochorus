import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV } from './contentNav';
import { EMBLEM_ART } from './emblems';
import { SECTION_MARKS } from './sections';

const FLEURON = readFileSync(join(process.cwd(), 'src/lib/components/Fleuron.svelte'), 'utf-8');

describe('section marks', () => {
	it('gives every primary section an ornament, an emblem and its nav icon', () => {
		for (const { section, icon } of PRIMARY_NAV) {
			const marks = SECTION_MARKS[section];
			expect(marks, `${section} has no marks`).toBeTruthy();
			expect(marks.icon).toBe(icon);
			expect(EMBLEM_ART[marks.emblem], `${section}: no emblem art "${marks.emblem}"`).toBeTruthy();
		}
	});

	it('gives each section its own ornament and emblem', () => {
		const marks = Object.values(SECTION_MARKS);
		expect(new Set(marks.map((m) => m.ornament)).size).toBe(marks.length);
		expect(new Set(marks.map((m) => m.emblem)).size).toBe(marks.length);
	});

	it('draws every ornament a section names (a misspelt one would fall back to the leaf)', () => {
		for (const { ornament } of Object.values(SECTION_MARKS))
			expect(FLEURON, `Fleuron draws no "${ornament}"`).toContain(`ornament === '${ornament}'`);
	});
});
