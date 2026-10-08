import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { hookFor } from './bookHooks';

const en: Record<string, string> = JSON.parse(
	readFileSync(resolve(import.meta.dirname, '../../messages/en.json'), 'utf8')
);
const PREFIX = 'audience_hook_';
const hooked = Object.keys(en)
	.filter((k) => k.startsWith(PREFIX))
	.map((k) => k.slice(PREFIX.length).replace(/_/g, '-'));

describe('hookFor', () => {
	it("is the book's catalogue line", () => {
		expect(hookFor('all-of-grace')).toBe(en.audience_hook_all_of_grace);
	});

	it("is '' for a book without one", () => {
		expect(hookFor('no-such-book')).toBe('');
	});

	it("names only real books, so a renamed slug can't strand its hook", () => {
		const fixtures = resolve(import.meta.dirname, '../../../backend/library/fixtures/content/books');
		expect(hooked.length).toBeGreaterThan(0);
		for (const slug of hooked) expect(existsSync(resolve(fixtures, `${slug}.en.json`)), slug).toBe(true);
	});
});
