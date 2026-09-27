import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';
import { locales } from '$lib/paraglide/runtime';
import { homeShareCardUrl } from './homeShareCard';

const STATIC = path.resolve(__dirname, '../../static');

describe('home share card', () => {
	// The home page names a card for whatever locale it is prerendered in, so a
	// locale added to the interface without running `npm run og:home` would
	// hand every scraper of that home page a 404.
	it.each([...locales])('%s has a 1200x630 card', async (locale) => {
		const file = path.join(STATIC, homeShareCardUrl(locale));
		expect(fs.existsSync(file), `${file} — run \`npm run og:home\``).toBe(true);
		const { width, height, format } = await sharp(file).metadata();
		expect({ width, height, format }).toEqual({
			width: 1200,
			height: 630,
			format: 'jpeg'
		});
	});
});
