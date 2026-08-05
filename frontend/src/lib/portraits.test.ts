import { describe, expect, it } from 'vitest';
import { readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { PORTRAIT_POSITION, PORTRAIT_POSITION_DEFAULT, portraitPosition } from './portraits';

/**
 * The focal-point table is hand-read off the image files, so its one real
 * failure mode is drifting away from them: a portrait added with no entry
 * silently falls back to the default crop, and an entry left behind after a
 * file is renamed or removed is dead weight nobody will ever notice.
 *
 * Both directions are checked against `static/portraits/` on disk — the same
 * trick `typeScale.test.ts` uses, since vitest runs with cwd at `frontend/`.
 */
const files = readdirSync(resolve(process.cwd(), 'static/portraits'))
	.filter((f) => f.endsWith('.jpg'))
	.map((f) => f.replace(/\.jpg$/, ''));

describe('portrait focal points', () => {
	it('finds the portraits at all', () => {
		// Guards the test itself: a moved directory would make the rest vacuous.
		expect(files.length).toBeGreaterThan(20);
	});

	it('covers every portrait in the repo', () => {
		for (const slug of files) {
			expect(PORTRAIT_POSITION, `no focal point for ${slug}.jpg`).toHaveProperty(slug);
		}
	});

	it('has no entry without a portrait', () => {
		for (const slug of Object.keys(PORTRAIT_POSITION)) {
			expect(files, `${slug} has a focal point but no portrait`).toContain(slug);
		}
	});

	it('reads as an object-position with x pinned at 50%', () => {
		for (const [slug, pos] of Object.entries(PORTRAIT_POSITION)) {
			expect(pos, slug).toMatch(/^50% (100|\d{1,2})%$/);
		}
	});

	it('falls back for an author with no entry', () => {
		expect(portraitPosition('someone-new')).toBe(PORTRAIT_POSITION_DEFAULT);
		expect(portraitPosition(undefined)).toBe(PORTRAIT_POSITION_DEFAULT);
		expect(portraitPosition('')).toBe(PORTRAIT_POSITION_DEFAULT);
	});

	it('uses the table when there is one', () => {
		expect(portraitPosition('charles-finney')).toBe('50% 0%');
	});
});
