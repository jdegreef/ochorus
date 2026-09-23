import { beforeEach, describe, expect, it, vi } from 'vitest';

const pushed: string[] = [];
vi.mock('./readingSync', () => ({ readingSync: { pushShelf: (s: { id: string }) => pushed.push(s.id) } }));

import { customShelves } from './customShelves.svelte';

beforeEach(() => {
	localStorage.clear();
	pushed.length = 0;
});

describe('customShelves', () => {
	it('creates, lists, renames and pushes each change', () => {
		expect(customShelves.create('   ')).toBeNull();
		const id = customShelves.create('  Lent 2027  ', 'humility')!;
		expect(customShelves.list().map((s) => s.name)).toEqual(['Lent 2027']);
		expect(customShelves.has(id, 'humility')).toBe(true);
		customShelves.rename(id, 'Easter');
		expect(customShelves.get(id)?.name).toBe('Easter');
		expect(pushed).toEqual([id, id]);
	});

	it('adds and removes books, keeping the removal as a tombstone', () => {
		const id = customShelves.create('Group')!;
		customShelves.setBook(id, 'a', true);
		customShelves.setBook(id, 'b', true);
		customShelves.setBook(id, 'a', false);
		expect([...customShelves.books(id).keys()]).toEqual(['b']);
		expect(customShelves.get(id)?.books.find((b) => b.slug === 'a')?.removed).toBe(true);
	});

	it('deletes to a tombstone and restores', () => {
		const id = customShelves.create('Gone')!;
		customShelves.setDeleted(id, true);
		expect(customShelves.list()).toEqual([]);
		expect(customShelves.get(id)?.deleted).toBe(true);
		expect(customShelves.books(id).size).toBe(0);
		customShelves.setDeleted(id, false);
		expect(customShelves.list().map((s) => s.id)).toEqual([id]);
	});
});
