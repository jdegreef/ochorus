import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The app's side, with the Capacitor plugins stood in for: what each platform
// function asks of the phone.
const m = vi.hoisted(() => ({
	backButton: undefined as undefined | ((e: { canGoBack: boolean }) => void),
	share: vi.fn(),
	writeFile: vi.fn(),
	browserOpen: vi.fn(),
	exitApp: vi.fn(),
	setStyle: vi.fn(),
	setBackgroundColor: vi.fn(),
	hide: vi.fn(),
	platform: 'ios'
}));

vi.mock('@capacitor/share', () => ({ Share: { share: m.share } }));
vi.mock('@capacitor/filesystem', () => ({
	Directory: { Cache: 'CACHE' },
	Filesystem: { writeFile: m.writeFile }
}));
vi.mock('@capacitor/browser', () => ({ Browser: { open: m.browserOpen } }));
vi.mock('@capacitor/app', () => ({
	App: {
		addListener: vi.fn((_: string, fn: (e: { canGoBack: boolean }) => void) => {
			m.backButton = fn;
			return Promise.resolve({ remove: vi.fn() });
		}),
		exitApp: m.exitApp
	}
}));
vi.mock('@capacitor/status-bar', () => ({
	Style: { Dark: 'DARK', Light: 'LIGHT' },
	StatusBar: { setStyle: m.setStyle, setBackgroundColor: m.setBackgroundColor }
}));
vi.mock('@capacitor/splash-screen', () => ({ SplashScreen: { hide: m.hide } }));
vi.mock('@capacitor/core', () => ({ Capacitor: { getPlatform: () => m.platform } }));

import { openExternal, setStatusBar, share, shareFile, startAppShell } from './native';

beforeEach(() => {
	for (const f of [m.share, m.writeFile, m.browserOpen, m.exitApp, m.setStyle, m.setBackgroundColor, m.hide]) {
		f.mockReset();
	}
	m.hide.mockResolvedValue(undefined);
	m.platform = 'ios';
});

describe('native share', () => {
	it('opens the share sheet', async () => {
		m.share.mockResolvedValue({});
		expect(await share({ title: 'T', url: 'https://ochorus.com/x/' })).toBe('shared');
		expect(m.share).toHaveBeenCalledWith({ title: 'T', url: 'https://ochorus.com/x/' });
	});
	it('reads a dismissed sheet as aborted, anything else as unavailable', async () => {
		m.share.mockRejectedValue(new Error('Share canceled'));
		expect(await share({ url: 'u' })).toBe('aborted');
		m.share.mockRejectedValue(new Error('boom'));
		expect(await share({ url: 'u' })).toBe('unavailable');
	});
});

describe('native shareFile', () => {
	it('writes the file to the cache, then shares it by path', async () => {
		m.writeFile.mockResolvedValue({ uri: 'file:///cache/card.png' });
		m.share.mockResolvedValue({});
		const blob = new Blob(['png'], { type: 'image/png' });
		expect(await shareFile(blob, 'card.png', 'a quote')).toBe('shared');
		expect(m.writeFile).toHaveBeenCalledWith({ path: 'card.png', data: btoa('png'), directory: 'CACHE' });
		expect(m.share).toHaveBeenCalledWith({ files: ['file:///cache/card.png'], text: 'a quote' });
	});
	it('is unavailable when the file cannot be written', async () => {
		m.writeFile.mockRejectedValue(new Error('disk'));
		expect(await shareFile(new Blob(['x']), 'c.png', '')).toBe('unavailable');
		expect(m.share).not.toHaveBeenCalled();
	});
});

describe('native openExternal / setStatusBar', () => {
	it('opens the system browser', async () => {
		await openExternal('https://example.org/');
		expect(m.browserOpen).toHaveBeenCalledWith({ url: 'https://example.org/' });
	});
	it('styles the bar for the theme; colours it only on Android', async () => {
		await setStatusBar('#16130f', true);
		expect(m.setStyle).toHaveBeenCalledWith({ style: 'DARK' });
		expect(m.setBackgroundColor).not.toHaveBeenCalled();
		m.platform = 'android';
		await setStatusBar('#faf6ef', false);
		expect(m.setStyle).toHaveBeenLastCalledWith({ style: 'LIGHT' });
		expect(m.setBackgroundColor).toHaveBeenCalledWith({ color: '#faf6ef' });
	});
	it('never throws where the bar cannot be changed', async () => {
		m.platform = 'android';
		m.setBackgroundColor.mockRejectedValue(new Error('Not available on Android 15+'));
		await expect(setStatusBar('#faf6ef', false)).resolves.toBeUndefined();
	});
});

describe('startAppShell', () => {
	const navigate = vi.fn();
	let root = false;
	let routerSaw: boolean[] = [];
	// Stands in for SvelteKit's router: notes whether the shell claimed the
	// click, then keeps jsdom from following the link.
	const routerSpy = (e: Event) => {
		routerSaw.push(e.defaultPrevented);
		e.preventDefault();
	};

	// Once: it installs document-wide listeners.
	startAppShell({ navigate, isRoot: () => root, siteUrl: 'https://ochorus.com' });
	document.addEventListener('click', routerSpy);

	afterEach(() => {
		document.body.innerHTML = '';
		navigate.mockReset();
		routerSaw = [];
		root = false;
	});

	const tap = (html: string, init: MouseEventInit = {}) => {
		document.body.innerHTML = html;
		document.querySelector('a')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ...init }));
	};

	it('opens another origin in the system browser and keeps the router out', () => {
		tap('<a href="https://en.wikipedia.org/wiki/Prayer">w</a>');
		expect(m.browserOpen).toHaveBeenCalledWith({ url: 'https://en.wikipedia.org/wiki/Prayer' });
		expect(routerSaw).toEqual([true]);
	});

	it('opens a website-only file on the website', () => {
		tap('<a href="/feed.xml">feed</a>');
		expect(m.browserOpen).toHaveBeenCalledWith({ url: 'https://ochorus.com/feed.xml' });
	});

	it('routes an absolute ochorus.com page link inside the app', () => {
		tap('<a href="https://ochorus.com/books/humility/">h</a>');
		expect(navigate).toHaveBeenCalledWith('/books/humility/');
		expect(m.browserOpen).not.toHaveBeenCalled();
	});

	it('leaves in-app links and modified clicks to the router', () => {
		tap('<a href="/books/">b</a>');
		tap('<a href="https://example.org/">x</a>', { metaKey: true });
		expect(m.browserOpen).not.toHaveBeenCalled();
		expect(routerSaw).toEqual([false, false]);
	});

	it('Back closes an open sheet first', () => {
		document.body.innerHTML = '<div aria-modal="true"><button>x</button></div>';
		const esc = vi.fn();
		document.addEventListener('keydown', esc);
		m.backButton!({ canGoBack: true });
		expect(esc).toHaveBeenCalledTimes(1);
		expect((esc.mock.calls[0][0] as KeyboardEvent).key).toBe('Escape');
		// …and if that sheet ignores Escape, the next press navigates.
		const back = vi.spyOn(history, 'back').mockImplementation(() => {});
		m.backButton!({ canGoBack: true });
		expect(back).toHaveBeenCalled();
		document.removeEventListener('keydown', esc);
	});

	it('Back goes back in history, and leaves the app at the root or with no history', () => {
		const back = vi.spyOn(history, 'back').mockImplementation(() => {});
		m.backButton!({ canGoBack: true });
		expect(back).toHaveBeenCalledTimes(1);
		m.backButton!({ canGoBack: false });
		expect(m.exitApp).toHaveBeenCalledTimes(1);
		root = true;
		m.backButton!({ canGoBack: true });
		expect(m.exitApp).toHaveBeenCalledTimes(2);
		expect(back).toHaveBeenCalledTimes(1);
	});

	it('hides the splash on the first frame', async () => {
		startAppShell({ navigate, isRoot: () => root, siteUrl: 'https://ochorus.com' });
		await new Promise((r) => requestAnimationFrame(() => r(null)));
		expect(m.hide).toHaveBeenCalled();
	});
});
