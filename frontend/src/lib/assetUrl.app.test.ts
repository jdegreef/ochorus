import { describe, expect, it, vi } from 'vitest';

// This file runs assetUrl as the native app's bundle sees it. The rest of the
// suite runs the website's (vitest.config.ts pins `__APP__` to false).
vi.mock('./platform', () => ({ IS_APP: true }));
vi.mock('./config', () => ({ SITE_URL: 'https://ochorus.com' }));

const { assetHtml, assetSrcset, assetUrl } = await import('./assetUrl');

describe('assetUrl in the native app', () => {
	it('loads unbundled images from the site', () => {
		expect(assetUrl('/covers/humility.png')).toBe('https://ochorus.com/covers/humility.png');
		expect(assetUrl('/portraits/andrew-murray.jpg')).toBe('https://ochorus.com/portraits/andrew-murray.jpg');
		expect(assetSrcset('/covers/humility-320.webp 1x, /covers/humility-640.webp 2x')).toBe(
			'https://ochorus.com/covers/humility-320.webp 1x, https://ochorus.com/covers/humility-640.webp 2x'
		);
		expect(assetHtml('<img src="/illustrations/x/1.jpg" alt="A">')).toBe(
			'<img src="https://ochorus.com/illustrations/x/1.jpg" alt="A">'
		);
	});

	it('keeps bundled files local and passes empty values through', () => {
		expect(assetUrl('/emblems/prayer.svg')).toBe('/emblems/prayer.svg');
		expect(assetUrl('')).toBe('');
		expect(assetUrl(undefined)).toBeUndefined();
		expect(assetSrcset(undefined)).toBeUndefined();
	});
});
