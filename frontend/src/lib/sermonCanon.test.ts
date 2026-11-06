import { describe, expect, it } from 'vitest';
import { CANON, CANON_MIN_BOOKS, canonGrid } from './sermonCanon';
import { BIBLE_SECTIONS, HEAT_LEVELS } from './scriptureIndex';

const on = (order: number, n = 1, name = CANON[order - 1][0]) =>
	Array.from({ length: n }, () => ({ scripture_book: name, scripture_book_order: order }));

/** One sermon on each of the first `k` books — enough to clear the floor. */
const spread = (k = CANON_MIN_BOOKS) => Array.from({ length: k }, (_, i) => on(i + 1)).flat();

describe('CANON', () => {
	it('is the 66 books, split where BIBLE_SECTIONS splits the testaments', () => {
		expect(CANON).toHaveLength(66);
		const lastOld = Math.max(...BIBLE_SECTIONS.filter((s) => s.testament === 'old').map((s) => s.to));
		expect(CANON[lastOld - 1][0]).toBe('Malachi');
		expect(CANON[lastOld][0]).toBe('Matthew');
		expect(new Set(CANON.map(([n]) => n)).size).toBe(66);
		expect(new Set(CANON.map(([, a]) => a)).size).toBe(66);
	});
});

describe('canonGrid', () => {
	it('leaves the grid out below the floor of distinct books', () => {
		expect(canonGrid([])).toBeNull();
		expect(canonGrid(spread(CANON_MIN_BOOKS - 1))).toBeNull();
		// Unparsed references (a translated sermon's) don't count toward it.
		const unparsed = Array.from({ length: 40 }, () => ({ scripture_book: null, scripture_book_order: null }));
		expect(canonGrid([...spread(CANON_MIN_BOOKS - 1), ...unparsed])).toBeNull();
	});

	it('lists every book in both testaments, empty ones at count 0 and heat 0', () => {
		const g = canonGrid(spread())!;
		expect(g.old).toHaveLength(39);
		expect(g.new).toHaveLength(27);
		expect(g.old[0]).toMatchObject({ name: 'Genesis', abbr: 'Gen', count: 1 });
		expect(g.new.at(-1)).toMatchObject({ name: 'Revelation', count: 0, heat: 0 });
	});

	it('shades any book with sermons at least 1, the busiest at the top', () => {
		const g = canonGrid([...spread(), ...on(43, 58)])!; // John: 58
		const john = g.new.find((c) => c.name === 'John')!;
		expect(john.count).toBe(58);
		expect(john.heat).toBe(HEAT_LEVELS - 1);
		for (const c of [...g.old, ...g.new]) {
			expect(c.heat >= 1).toBe(c.count > 0);
			expect(c.heat).toBeLessThan(HEAT_LEVELS);
		}
		// A square-root scale: a book with a quarter of John's sits mid-way.
		const mid = canonGrid([...spread(), ...on(43, 58), ...on(19, 15)])!.old[18];
		expect(mid.count).toBe(15);
		expect(mid.heat).toBeGreaterThan(1);
		expect(mid.heat).toBeLessThan(HEAT_LEVELS - 1);
	});

	it('filters on the payload name, and ignores books outside the 66', () => {
		const g = canonGrid([...spread(), ...on(19, 1, 'Psalm'), ...on(70, 3, 'Ecclesiasticus')])!;
		expect(g.old[18].name).toBe('Psalm');
		expect([...g.old, ...g.new].reduce((n, c) => n + c.count, 0)).toBe(CANON_MIN_BOOKS + 1);
	});
});
