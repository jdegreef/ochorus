import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { artSlug, SEASON_ART } from './heroArt';

const SERVED = join(process.cwd(), 'static', 'covers', 'art', 'credits.json');
const BACKEND = join(process.cwd(), '..', 'backend', 'library', 'data', 'art_credits.json');

describe('the hero painting', () => {
	it('reads the book slug off a painting url', () => {
		expect(artSlug('/covers/art/religious-affections-640.webp')).toBe('religious-affections');
		expect(artSlug('/covers/art/waiting-on-god.jpg')).toBe('waiting-on-god');
		expect(artSlug('/covers/art/power-from-on-high-new-testament-320.webp')).toBe(
			'power-from-on-high-new-testament'
		);
		// A numbered ground is its own file, not a width of another.
		expect(artSlug('/covers/art/humility-2.jpg')).toBe('humility-2');
		expect(artSlug('/covers/humility-2.jpg')).toBeNull();
	});

	it('hangs a real, credited painting in every season', () => {
		const credits = JSON.parse(readFileSync(SERVED, 'utf-8'));
		for (const [season, url] of Object.entries(SEASON_ART)) {
			expect(existsSync(join(process.cwd(), 'static', url)), `${season}: ${url}`).toBe(true);
			expect(credits[artSlug(url)!], `${season} has no credit`).toBeTruthy();
		}
	});

	it('serves the credits the backend exported, byte for byte', () => {
		// One script writes both; if this fails, run
		// `cd backend && python scripts/export_art_credits.py`.
		expect(readFileSync(SERVED, 'utf-8')).toBe(readFileSync(BACKEND, 'utf-8'));
	});
});
