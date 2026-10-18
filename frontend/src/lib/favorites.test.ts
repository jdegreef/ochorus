import { beforeEach, describe, expect, it, vi } from 'vitest';
import { favorites } from './favorites.svelte';
import { pendingAt } from './removals';
import { FAVORITES_KEY } from './reading-schema';

beforeEach(() => localStorage.clear());

describe('favorites store', () => {
	it('toggles a favorite on and off', () => {
		expect(favorites.has('author', 'andrew-murray')).toBe(false);
		favorites.toggle('author', 'andrew-murray');
		expect(favorites.has('author', 'andrew-murray')).toBe(true);
		favorites.toggle('author', 'andrew-murray');
		expect(favorites.has('author', 'andrew-murray')).toBe(false);
	});

	it('keeps kinds separate for the same slug', () => {
		favorites.toggle('book', 'humility');
		expect(favorites.has('book', 'humility')).toBe(true);
		expect(favorites.has('plan', 'humility')).toBe(false);
	});

	it('lists all favorites most-recent-first with parsed kinds', () => {
		favorites.toggle('author', 'c-h-spurgeon');
		favorites.toggle('plan', 'school-of-prayer');
		const all = favorites.all();
		expect(all.length).toBe(2);
		expect(favorites.count()).toBe(2);
		// Slugs containing hyphens survive the "kind:slug" key round-trip.
		expect(all.map((e) => [e.kind, e.slug])).toContainEqual(['author', 'c-h-spurgeon']);
		expect(all.map((e) => [e.kind, e.slug])).toContainEqual(['plan', 'school-of-prayer']);
	});
});

describe('un-hearting is remembered until the account confirms it', () => {
	it('records a pending removal, and a re-heart lifts it', () => {
		favorites.toggle('book', 'humility');
		favorites.toggle('book', 'humility');
		expect(pendingAt('favorite', 'book', 'humility')).toBeTypeOf('number');
		favorites.toggle('book', 'humility');
		expect(pendingAt('favorite', 'book', 'humility')).toBeNull();
	});
});

describe('reading the store', () => {
	it('parses it once however many hearts ask, and re-reads a changed value', () => {
		favorites.toggle('quote', 'q1');
		const parse = vi.spyOn(JSON, 'parse');
		for (let i = 0; i < 50; i++) favorites.has('quote', `q${i}`);
		expect(parse.mock.calls.length).toBeLessThanOrEqual(1);
		// A write that didn't come through the store (a sign-in merge, another
		// tab) is a new stored value, and is read fresh.
		localStorage.setItem(FAVORITES_KEY, JSON.stringify({ 'quote:q2': 1 }));
		expect(favorites.has('quote', 'q2')).toBe(true);
		expect(favorites.has('quote', 'q1')).toBe(false);
		parse.mockRestore();
	});

	it('a failed write leaves the read value untouched', () => {
		favorites.toggle('book', 'humility');
		const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('quota');
		});
		favorites.toggle('book', 'humility');
		set.mockRestore();
		// The removal never reached storage, so the heart is still stored.
		expect(favorites.has('book', 'humility')).toBe(true);
	});
});
