import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { seriesMeta } from './emblemNames';
// Shared with the generator, so the two cannot disagree about what a card's content is.
import { compositionDigest, contentDigest, seriesCards } from '../../scripts/series-og-content.mjs';

/**
 * The series share cards (`npm run og:series`) against what they were drawn
 * from: every series with an English volume has a card, and each card's
 * strings, volume count, cover bytes, accent and drawing code are as they
 * stand today. INPUTS, not output: a change in satori or resvg is invisible.
 */
const manifest: {
	composition: string;
	cards: Record<string, { content: string; accent: string }>;
} = JSON.parse(readFileSync(join(process.cwd(), 'static', 'og', 'series', 'og-manifest.json'), 'utf-8'));
const RERUN = 'run `cd frontend && npm run og:series`';
const cards = seriesCards();

describe('series share cards', () => {
	it('has a card for every series with an English volume, and only those', () => {
		expect(Object.keys(manifest.cards).sort(), RERUN).toEqual(Object.keys(cards).sort());
	});

	it('was drawn from the content and accent each series has today', () => {
		const stale = Object.entries(cards)
			.filter(([slug, c]) => {
				const m = manifest.cards[slug];
				return !m || m.content !== contentDigest(c) || m.accent !== seriesMeta(slug).accent;
			})
			.map(([slug]) => slug);
		expect(stale, `a series' title, tagline, volumes, a cover or its accent changed — ${RERUN}`).toEqual([]);
	});

	it('was drawn by the drawing code as it stands', () => {
		expect(compositionDigest(), `the card generator changed — ${RERUN}`).toBe(manifest.composition);
	});
});
