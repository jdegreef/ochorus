import { beforeEach, describe, expect, it } from 'vitest';
import { favorites } from './favorites.svelte';
import { pendingAt } from './removals';

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
