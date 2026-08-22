import { describe, expect, it } from 'vitest';
import { EMBLEM_ART, emblemHue, type EmblemName } from './emblems';
import { EMBLEM_HUES } from './emblemHues';

/**
 * The committed map is what the app ships; `emblemHue` is what it means. This
 * is the only thing keeping them the same colour, so it checks every entry
 * rather than a sample.
 */
describe('precomputed emblem hues', () => {
	const names = Object.keys(EMBLEM_ART) as EmblemName[];

	it('covers every emblem, with nothing left over', () => {
		expect(Object.keys(EMBLEM_HUES).sort()).toEqual([...names].sort());
	});

	it('matches what emblemHue derives, for all of them', () => {
		const drifted = names.filter((n) => EMBLEM_HUES[n] !== emblemHue(n));
		expect(
			drifted.map((n) => `${n}: committed ${EMBLEM_HUES[n]}, derived ${emblemHue(n)}`),
			'run `npm run emblem:hues` and commit src/lib/emblemHues.ts'
		).toEqual([]);
	});
});
