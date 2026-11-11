import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { JOURNEY_MAPS, MAP_HEIGHT, MAP_WIDTH, journeyMapFor } from './journeyMaps';
import { journeyStates, roadPath } from './journeyMap';

const BOOKS = resolve(__dirname, '../../../backend/library/fixtures/content/books');

/** A chapter's plain text, from the edition's committed fixture file. */
function chapterTexts(slug: string, language: string): Map<number, string> {
	const rows = JSON.parse(readFileSync(`${BOOKS}/${slug}.${language}.json`, 'utf8')) as {
		model: string;
		fields: { order: number; body_html: string };
	}[];
	return new Map(
		rows
			.filter((r) => r.model === 'library.chapter')
			.map((r) => [r.fields.order, r.fields.body_html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')])
	);
}

describe('JOURNEY_MAPS', () => {
	for (const [slug, map] of Object.entries(JOURNEY_MAPS)) {
		describe(slug, () => {
			const texts = chapterTexts(slug, map.language);

			it('places every stop in the chapter whose text names it', () => {
				// The mapping is read off the book, not guessed: each stop carries a
				// phrase from its chapter. A re-chaptered edition fails here
				// rather than sending a reader to the wrong chapter.
				for (const stop of map.stops) {
					expect(texts.get(stop.chapter), `${stop.name}: no chapter ${stop.chapter}`).toBeDefined();
					expect(texts.get(stop.chapter), `${stop.name} in chapter ${stop.chapter}`).toContain(stop.evidence);
				}
			});

			it('runs in reading order, on the canvas, one name per stop', () => {
				const chapters = map.stops.map((s) => s.chapter);
				expect(chapters).toEqual([...chapters].sort((a, b) => a - b));
				expect(new Set(map.stops.map((s) => s.name)).size).toBe(map.stops.length);
				for (const s of map.stops) {
					expect(s.x).toBeGreaterThan(0);
					expect(s.x).toBeLessThan(MAP_WIDTH);
					expect(s.y).toBeGreaterThan(0);
					expect(s.y).toBeLessThan(MAP_HEIGHT);
				}
			});
		});
	}

	it('is offered only on the edition whose words it uses', () => {
		expect(journeyMapFor('pilgrims-progress', 'en')).not.toBeNull();
		expect(journeyMapFor('pilgrims-progress', 'sw')).toBeNull();
		expect(journeyMapFor('humility', 'en')).toBeNull();
	});
});

describe('journeyStates', () => {
	const stops = [2, 2, 3, 4, 4, 7].map((chapter) => ({ chapter }));
	const at = (current: number | null, furthest = current, finished = false) =>
		journeyStates(stops, { current, furthest, finished });

	it('puts a new reader at the start of the road with nothing passed', () => {
		expect(at(null)).toEqual(Array(6).fill('ahead'));
		// Still in the preface, before the first place.
		expect(at(1)).toEqual(Array(6).fill('ahead'));
	});
	it('stands the reader at the first place of the chapter they are in', () => {
		expect(at(4)).toEqual(['passed', 'passed', 'passed', 'here', 'ahead', 'ahead']);
		expect(at(2)).toEqual(['here', 'ahead', 'ahead', 'ahead', 'ahead', 'ahead']);
	});
	it('in a chapter with no place, is just past the last one', () => {
		expect(at(5)).toEqual(['passed', 'passed', 'passed', 'passed', 'here', 'ahead']);
	});
	it('falls back to the furthest chapter, and passes everything once finished', () => {
		expect(at(null, 3)).toEqual(['passed', 'passed', 'here', 'ahead', 'ahead', 'ahead']);
		expect(at(3, 3, true)).toEqual(Array(6).fill('passed'));
	});
});

describe('roadPath', () => {
	it('starts at the first stop and bends through each', () => {
		const d = roadPath([
			{ x: 0, y: 0 },
			{ x: 10, y: 10 },
			{ x: 20, y: 0 }
		]);
		expect(d.startsWith('M0,0 C')).toBe(true);
		expect(d.endsWith(' 20,0')).toBe(true);
		expect(d.match(/C/g)).toHaveLength(2);
		expect(roadPath([])).toBe('');
	});
});
