import { describe, expect, it } from 'vitest';
import { apiFile, imageFile, offlineFileUrl } from './offlineFiles';

describe('offline file names', () => {
	it('stores an API response as one flat file, reversibly', () => {
		const key = '/api/library/books/humility/chapters/3/?language=es';
		const file = apiFile(key);
		expect(file.startsWith('api/')).toBe(true);
		expect(file.slice(4)).not.toMatch(/[/?=]/);
		expect(decodeURIComponent(file.slice(4, -'.json'.length))).toBe(key);
	});

	it('keeps a site image at its own path, extension and all', () => {
		expect(imageFile('/covers/humility-320.webp')).toBe('img/covers/humility-320.webp');
		expect(imageFile('/illustrations/humility/plate.jpg')).toBe('img/illustrations/humility/plate.jpg');
	});

	it('saves nothing that could leave the folder or does not name a file', () => {
		for (const bad of ['covers/x.jpg', '/', '/covers/../x', '/covers//x', '/covers/x.jpg?v=2', '/covers/a%2Fb', 'https://x/y']) {
			expect(imageFile(bad)).toBeNull();
		}
	});

	it('serves a file under the launch’s base URL', () => {
		expect(offlineFileUrl('https://localhost/_capacitor_file_/data/offline/', 'img/covers/a b.jpg')).toBe(
			'https://localhost/_capacitor_file_/data/offline/img/covers/a%20b.jpg'
		);
	});
});
