import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

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
	// Never reset: the splash is hidden on a frame, which can land at any point.
	hide: vi.fn(() => Promise.resolve()),
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

import { backStack } from './back';
import { openExternal, setStatusBar, share, shareFile, startAppShell } from './native';

beforeEach(() => {
	for (const f of [m.share, m.writeFile, m.browserOpen, m.exitApp, m.setStyle, m.setBackgroundColor]) {
		f.mockReset();
	}
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
	it('styles the bar for the theme; colours it only on Android, in the nav’s colour', async () => {
		await setStatusBar('#16130f', true);
		expect(m.setStyle).toHaveBeenCalledWith({ style: 'DARK' });
		expect(m.setBackgroundColor).not.toHaveBeenCalled();
		m.platform = 'android';
		await setStatusBar('#faf6ef', false);
		expect(m.setStyle).toHaveBeenLastCalledWith({ style: 'LIGHT' });
		// No nav colour to read: the theme's ground.
		expect(m.setBackgroundColor).toHaveBeenLastCalledWith({ color: '#faf6ef' });
		document.documentElement.style.setProperty('--surface-2', '#f4eee3');
		await setStatusBar('#faf6ef', false);
		expect(m.setBackgroundColor).toHaveBeenLastCalledWith({ color: '#f4eee3' });
		document.documentElement.style.removeProperty('--surface-2');
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
	// Stands in for SvelteKit's router (on <html>, after <body>): notes whether
	// the shell claimed the click, then keeps jsdom from following the link.
	const routerSpy = (e: Event) => {
		routerSaw.push(e.defaultPrevented);
		e.preventDefault();
	};
	const hooks = { navigate, isRoot: () => root, siteUrl: 'https://ochorus.com' };

	beforeAll(() => {
		startAppShell(hooks);
		startAppShell(hooks); // idempotent: one set of listeners, one splash hide
		document.documentElement.addEventListener('click', routerSpy);
	});

	afterEach(() => {
		document.body.innerHTML = '';
		navigate.mockReset();
		routerSaw = [];
		root = false;
		while (backStack.size) backStack.pop();
		vi.restoreAllMocks();
	});

	const tap = (html: string, init: MouseEventInit = {}) => {
		document.body.innerHTML = html;
		document.querySelector('a')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ...init }));
	};

	it('hides the splash once, on the first frame', async () => {
		await new Promise((r) => requestAnimationFrame(() => r(null)));
		expect(m.hide).toHaveBeenCalledTimes(1);
		expect(m.backButton).toBeTypeOf('function');
	});

	it('opens another origin in the system browser and keeps the router out', () => {
		tap('<a href="https://en.wikipedia.org/wiki/Prayer">w</a>');
		expect(m.browserOpen).toHaveBeenCalledTimes(1);
		expect(m.browserOpen).toHaveBeenCalledWith({ url: 'https://en.wikipedia.org/wiki/Prayer' });
		expect(routerSaw).toEqual([true]);
	});

	it('opens a website-only file, and a download, on the website', () => {
		tap('<a href="/feed.xml">feed</a>');
		expect(m.browserOpen).toHaveBeenLastCalledWith({ url: 'https://ochorus.com/feed.xml' });
		tap('<a href="/pdfs/humility.pdf" download>pdf</a>');
		expect(m.browserOpen).toHaveBeenLastCalledWith({ url: 'https://ochorus.com/pdfs/humility.pdf' });
	});

	it('routes an absolute ochorus.com page link inside the app', () => {
		tap('<a href="https://ochorus.com/books/humility/">h</a>');
		expect(navigate).toHaveBeenCalledWith('/books/humility/');
		expect(m.browserOpen).not.toHaveBeenCalled();
	});

	it('opens an app page asked for in a new tab here', () => {
		tap('<a href="/books/humility/" target="_blank">h</a>');
		expect(navigate).toHaveBeenCalledWith('/books/humility/');
		expect(routerSaw).toEqual([true]);
	});

	it('gives a data-sveltekit-reload link a full load', () => {
		const assign = vi.fn();
		vi.spyOn(window, 'location', 'get').mockReturnValue({ ...window.location, href: location.href, assign });
		tap('<div data-sveltekit-reload><a href="https://ochorus.com/ar/books/">ar</a></div>');
		expect(assign).toHaveBeenCalledWith('/ar/books/');
		expect(navigate).not.toHaveBeenCalled();
	});

	it('leaves in-app links, modified clicks and handled clicks alone', () => {
		tap('<a href="/books/">b</a>');
		tap('<a href="https://example.org/">x</a>', { metaKey: true });
		// A component that handled the click itself (Svelte delegates to the
		// app's root element, inside <body>).
		document.body.innerHTML = '<div id="root"><a href="https://example.org/">x</a></div>';
		document.getElementById('root')!.addEventListener('click', (e) => e.preventDefault());
		document.querySelector('a')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
		expect(m.browserOpen).not.toHaveBeenCalled();
		expect(navigate).not.toHaveBeenCalled();
	});

	it('Back closes the topmost open overlay first, one per press', () => {
		const sheet = vi.fn();
		const menuInSheet = vi.fn();
		backStack.push(sheet);
		backStack.push(menuInSheet);
		const back = vi.spyOn(history, 'back').mockImplementation(() => {});
		m.backButton!({ canGoBack: true });
		expect(menuInSheet).toHaveBeenCalledTimes(1);
		expect(sheet).not.toHaveBeenCalled();
		m.backButton!({ canGoBack: true });
		expect(sheet).toHaveBeenCalledTimes(1);
		expect(back).not.toHaveBeenCalled();
		m.backButton!({ canGoBack: true });
		expect(back).toHaveBeenCalledTimes(1);
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
});
