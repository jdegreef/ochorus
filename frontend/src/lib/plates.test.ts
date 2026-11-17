import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { plateSrcset, plateVariants } from './plates';

const ROOT = resolve(__dirname, '../../static/illustrations');

describe('plate variants', () => {
	it('names a plate’s webp variants and leaves other pictures alone', () => {
		expect(plateSrcset('/illustrations/the-black-stair/b2-plate-03-mothwing-weather.jpg')).toBe(
			'/illustrations/the-black-stair/b2-plate-03-mothwing-weather-320.webp 1x, ' +
				'/illustrations/the-black-stair/b2-plate-03-mothwing-weather-640.webp 2x'
		);
		expect(plateVariants('/illustrations/fire-against-the-dark/land-of-gloamhaven.jpg')).toEqual([]);
	});

	// The series page asks for the variants, so a plate without them would draw
	// a broken picture. Run backend/scripts/build_plate_thumbs.py.
	it('every plate in static/illustrations has its variants', () => {
		const missing = (readdirSync(ROOT, { recursive: true }) as string[])
			.map((f) => `/illustrations/${f.replaceAll('\\', '/')}`)
			.flatMap(plateVariants)
			.filter((v) => !existsSync(join(ROOT, v.slice('/illustrations'.length))));
		expect(missing).toEqual([]);
	});
});
