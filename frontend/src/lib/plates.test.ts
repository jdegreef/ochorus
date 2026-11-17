import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { plateThumb } from './plates';

const ROOT = resolve(__dirname, '../../static/illustrations');

function walk(dir: string): string[] {
	return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
		e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]
	);
}

describe('plateThumb', () => {
	it('names a plate’s small twin and leaves other pictures alone', () => {
		expect(plateThumb('/illustrations/the-black-stair/b2-plate-03-mothwing-weather.jpg')).toBe(
			'/illustrations/the-black-stair/b2-plate-03-mothwing-weather-320.webp'
		);
		expect(plateThumb('/illustrations/fire-against-the-dark/land-of-gloamhaven.jpg')).toBeNull();
	});

	// The series page asks for the twin first, so a plate without one would
	// draw a broken picture. Run backend/scripts/build_plate_thumbs.py.
	it('every plate in static/illustrations has its twin', () => {
		const missing = walk(ROOT)
			.map((f) => f.slice(ROOT.length).replaceAll('\\', '/'))
			.map((f) => `/illustrations${f}`)
			.filter((src) => plateThumb(src))
			.filter((src) => !existsSync(join(ROOT, plateThumb(src)!.slice('/illustrations'.length))));
		expect(missing).toEqual([]);
	});
});
