import { afterEach, describe, expect, it, vi } from 'vitest';
import * as platform from './index';
import { openExternal, share, shareFile } from './web';

const err = (name: string) => Object.assign(new Error(), { name });

afterEach(() => {
	// @ts-expect-error test cleanup
	delete navigator.share;
	// @ts-expect-error test cleanup
	delete navigator.canShare;
	vi.restoreAllMocks();
});

describe('web share', () => {
	it('is unavailable without the Web Share API', async () => {
		expect(await share({ url: 'u' })).toBe('unavailable');
	});
	it('maps the outcomes', async () => {
		Object.assign(navigator, { share: vi.fn().mockResolvedValue(undefined) });
		expect(await share({ url: 'u' })).toBe('shared');
		Object.assign(navigator, { share: vi.fn().mockRejectedValue(err('AbortError')) });
		expect(await share({ url: 'u' })).toBe('aborted');
		Object.assign(navigator, { share: vi.fn().mockRejectedValue(err('NotAllowedError')) });
		expect(await share({ url: 'u' })).toBe('unavailable');
	});
});

describe('web shareFile', () => {
	const blob = new Blob(['png'], { type: 'image/png' });
	it('is unavailable where files cannot be shared', async () => {
		Object.assign(navigator, { share: vi.fn(), canShare: vi.fn(() => false) });
		expect(await shareFile(blob, 'card.png', 'hi')).toBe('unavailable');
		expect(navigator.share).not.toHaveBeenCalled();
	});
	it('shares the file with its text', async () => {
		const spy = vi.fn().mockResolvedValue(undefined);
		Object.assign(navigator, { share: spy, canShare: vi.fn(() => true) });
		expect(await shareFile(blob, 'card.png', 'hi')).toBe('shared');
		const sent = spy.mock.calls[0][0] as { files: File[]; text: string };
		expect(sent.text).toBe('hi');
		expect(sent.files[0].name).toBe('card.png');
		expect(sent.files[0].type).toBe('image/png');
	});
});

describe('web openExternal', () => {
	it('opens a new tab without an opener', async () => {
		const open = vi.spyOn(window, 'open').mockReturnValue(null);
		await openExternal('https://example.org/');
		expect(open).toHaveBeenCalledWith('https://example.org/', '_blank', 'noopener,noreferrer');
	});
});

describe('platform on the website', () => {
	it('is the website build in tests', () => {
		expect(platform.IS_APP).toBe(false);
	});
	it('uses the web side, and the app-only functions do nothing', async () => {
		expect(platform.canShare()).toBe(false);
		Object.assign(navigator, { share: vi.fn().mockResolvedValue(undefined) });
		expect(platform.canShare()).toBe(true);
		expect(await platform.share({ url: 'u' })).toBe('shared');
		await expect(platform.setStatusBar('#000000', true)).resolves.toBeUndefined();
		platform.startAppShell({ navigate: vi.fn(), isRoot: () => true, siteUrl: 'https://ochorus.com' });
		expect(document.documentElement.hasAttribute('data-app')).toBe(false);
	});
});
