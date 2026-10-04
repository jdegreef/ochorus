import { afterEach, describe, expect, it, vi } from 'vitest';
import { nativeShare, shareLinks } from './share';

describe('shareLinks', () => {
	it('encodes title and url, and keeps mailto in the same tab', () => {
		const links = shareLinks('A & B', 'https://x.test/a?b=1', 'Email');
		expect(links.map((l) => l.name)).toEqual(['WhatsApp', 'Facebook', 'Email']);
		expect(links[0].href).toBe('https://wa.me/?text=A%20%26%20B%20https%3A%2F%2Fx.test%2Fa%3Fb%3D1');
		expect(links[2].href.startsWith('mailto:?subject=A%20%26%20B')).toBe(true);
		expect(links[2].newTab).toBe(false);
	});
});

describe('nativeShare', () => {
	afterEach(() => {
		// @ts-expect-error test cleanup
		delete navigator.share;
	});
	it('is unavailable without a share sheet', async () => {
		expect(await nativeShare('t', 'u')).toBe('unavailable');
	});
	it('reports a dismissed sheet as aborted', async () => {
		Object.assign(navigator, { share: vi.fn().mockRejectedValue(Object.assign(new Error(), { name: 'AbortError' })) });
		expect(await nativeShare('t', 'u')).toBe('aborted');
	});
	it('falls back on any other failure', async () => {
		Object.assign(navigator, { share: vi.fn().mockRejectedValue(Object.assign(new Error(), { name: 'NotAllowedError' })) });
		expect(await nativeShare('t', 'u')).toBe('unavailable');
	});
	it('shares when the sheet succeeds', async () => {
		Object.assign(navigator, { share: vi.fn().mockResolvedValue(undefined) });
		expect(await nativeShare('t', 'u')).toBe('shared');
	});
});
