import { describe, expect, it } from 'vitest';
import { fromServer, liveBooks, mergeServerShelves, mergeShelf, toServer, type CustomShelf } from './shelvesData';

const shelf = (over: Partial<CustomShelf> = {}): CustomShelf => ({
	id: 's-1',
	name: 'Lent',
	books: [],
	deleted: false,
	created: 100,
	updated: 100,
	...over
});
const b = (slug: string, at: number, removed = false) => ({ slug, at, removed });

describe('mergeShelf — the same rules as the API', () => {
	it('keeps books added on either side', () => {
		const m = mergeShelf(shelf({ books: [b('a', 1)] }), shelf({ books: [b('c', 2)] }));
		expect([...liveBooks(m).keys()]).toEqual(['a', 'c']);
	});

	it('lets a removal beat a stale add, and a later re-add beat the removal', () => {
		const removed = mergeShelf(shelf({ books: [b('a', 5, true)] }), shelf({ books: [b('a', 1)] }));
		expect(liveBooks(removed).size).toBe(0);
		const back = mergeShelf(removed, shelf({ books: [b('a', 9)] }));
		expect(liveBooks(back).has('a')).toBe(true);
	});

	it('takes the name and deleted state only from a newer write', () => {
		const cur = shelf({ name: 'Lent', updated: 200 });
		expect(mergeShelf(cur, shelf({ name: 'Old', updated: 150 })).name).toBe('Lent');
		expect(mergeShelf(cur, shelf({ name: 'Lent', deleted: true, updated: 300 })).deleted).toBe(true);
		expect(mergeShelf(cur, shelf({ name: 'Tie', updated: 200 })).name).toBe('Lent');
	});
});

describe('server shape', () => {
	it('round-trips, and folds the account into the device without dropping local-only shelves', () => {
		const s = shelf({ books: [b('a', 7)], updated: 300 });
		expect(fromServer(toServer(s))).toEqual(s);
		const local = { 's-local': shelf({ id: 's-local' }) };
		const merged = mergeServerShelves(local, [toServer(s), { ...toServer(s), shelf_id: '' }]);
		expect(Object.keys(merged).sort()).toEqual(['s-1', 's-local']);
	});
});
