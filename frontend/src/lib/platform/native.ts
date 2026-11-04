/**
 * The app's side of each $lib/platform function: Capacitor plugins. Loaded
 * only by index.ts behind `IS_APP` (a dynamic import of a build-time-dead
 * branch), so none of this — nor any @capacitor/* package — reaches the
 * website's bundle. ./web.ts is the website's side.
 */

import { App } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { Directory, Encoding, Filesystem } from '@capacitor/filesystem';
import { Preferences } from '@capacitor/preferences';
import { Share } from '@capacitor/share';
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';
import { isPlainPrimaryClick } from '../plainClick';
import { backStack } from './back';
import { linkTarget } from './links';
import type { ShareData, ShareResult } from './web';

/** Both plugins reject a dismissed sheet with a "Share canceled" error. */
const shareFailure = (err: unknown): ShareResult =>
	/cancel/i.test(String((err as Error)?.message ?? err)) ? 'aborted' : 'unavailable';

export async function share(data: ShareData): Promise<ShareResult> {
	try {
		await Share.share(data);
		return 'shared';
	} catch (err) {
		return shareFailure(err);
	}
}

function toBase64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(String(reader.result).replace(/^data:[^,]*,/, ''));
		reader.onerror = () => reject(reader.error);
		reader.readAsDataURL(blob);
	});
}

/** The share sheet takes files by path, not by bytes, so the file is written
 *  to the app's cache first (the OS clears it; no permission needed). */
export async function shareFile(blob: Blob, filename: string, text: string): Promise<ShareResult> {
	let uri: string;
	try {
		({ uri } = await Filesystem.writeFile({
			path: filename,
			data: await toBase64(blob),
			directory: Directory.Cache
		}));
	} catch {
		return 'unavailable';
	}
	try {
		await Share.share({ files: [uri], text });
		return 'shared';
	} catch (err) {
		return shareFailure(err);
	}
}

/** The system's in-app browser (Safari View Controller / a Chrome Custom
 *  Tab): the reader stays in the app and closes it to come back. Downloads go
 *  the same way — the browser views or saves the PDF / EPUB, which the app's
 *  web view cannot. */
export async function openExternal(url: string): Promise<void> {
	await Browser.open({ url });
}

/*
 * The phone's key-value store, for the reader's sign-in session
 * (./authStorage.ts): UserDefaults on iOS, SharedPreferences on Android —
 * kept across launches and app updates, unlike a web view's localStorage.
 */
export async function prefsGet(key: string): Promise<string | null> {
	return (await Preferences.get({ key })).value;
}

export async function prefsSet(key: string, value: string): Promise<void> {
	await Preferences.set({ key, value });
}

export async function prefsRemove(key: string): Promise<void> {
	await Preferences.remove({ key });
}

/** Status bar icons readable on the theme's ground. The ground under them is
 *  the page's own (the web view runs under the bar, and app.css paints the
 *  strip the nav's colour); only an Android that still draws an opaque bar
 *  takes a colour, the nav's (`--surface-2`, a hex per theme and palette),
 *  falling back to the theme's ground. */
export async function setStatusBar(color: string, dark: boolean): Promise<void> {
	try {
		await StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light });
		if (Capacitor.getPlatform() !== 'android') return;
		const nav = getComputedStyle(document.documentElement).getPropertyValue('--surface-2').trim();
		await StatusBar.setBackgroundColor({ color: /^#[0-9a-f]{6}$/i.test(nav) ? nav : color });
	} catch {
		/* Not available here (Android 15+ is edge to edge): the strip covers it. */
	}
}

/*
 * Downloaded books ("Download for offline"), under `offline/` in the app's
 * Library/NoCloud on iOS — kept until the reader removes them (not a cache the
 * OS may clear), and marked not to go into iCloud backups, as Apple asks of
 * content that can be downloaded again. On Android it is the app's private
 * files directory. `file` is a path inside `offline/` (./offlineFiles.ts).
 *
 * Images arrive through `Filesystem.downloadFile`: the request is native, so
 * the website's images need no CORS headers (a web view `fetch` of them would).
 * Its iOS side knows only CACHE / LIBRARY / Documents, though — it would put a
 * NoCloud download in Documents — so it downloads into the cache and the file
 * is then moved into place.
 */
const OFFLINE = Directory.LibraryNoCloud;
const ROOT = 'offline';
const at = (file: string) => `${ROOT}/${file}`;

/** A stored text, or null when there is none (or it cannot be read). */
export async function offlineReadText(file: string): Promise<string | null> {
	try {
		const { data } = await Filesystem.readFile({ path: at(file), directory: OFFLINE, encoding: Encoding.UTF8 });
		return typeof data === 'string' ? data : null;
	} catch {
		return null;
	}
}

/** Store a text; whether it was written. */
export async function offlineWriteText(file: string, text: string): Promise<boolean> {
	try {
		await Filesystem.writeFile({
			path: at(file),
			data: text,
			directory: OFFLINE,
			encoding: Encoding.UTF8,
			recursive: true
		});
		return true;
	} catch {
		return false;
	}
}

let downloads = 0;

/** Download `url` into `file`; whether it arrived. */
export async function offlineSaveFile(file: string, url: string): Promise<boolean> {
	const tmp = `offline-incoming/${Date.now()}-${downloads++}`;
	try {
		// Timeouts (ms), so one silent server cannot hold a download open.
		await Filesystem.downloadFile({
			url,
			path: tmp,
			directory: Directory.Cache,
			recursive: true,
			connectTimeout: 15_000,
			readTimeout: 30_000
		});
		const dest = at(file);
		// mkdir rejects a folder that is already there; the move below is the test.
		await Filesystem.mkdir({ path: dest.split('/').slice(0, -1).join('/'), directory: OFFLINE, recursive: true }).catch(
			() => {}
		);
		// A move does not overwrite, and a file already here (the same cover,
		// saved by another edition) may be one a kept download still shows: set
		// it aside, and put it back if the new one cannot take its place.
		const aside = `${dest}.old`;
		const hadOne = await Filesystem.rename({ from: dest, to: aside, directory: OFFLINE }).then(
			() => true,
			() => false
		);
		try {
			await Filesystem.rename({ from: tmp, directory: Directory.Cache, to: dest, toDirectory: OFFLINE });
		} catch (err) {
			if (hadOne) await Filesystem.rename({ from: aside, to: dest, directory: OFFLINE }).catch(() => {});
			throw err;
		}
		if (hadOne) await Filesystem.deleteFile({ path: aside, directory: OFFLINE }).catch(() => {});
		return true;
	} catch {
		await Filesystem.deleteFile({ path: tmp, directory: Directory.Cache }).catch(() => {});
		return false;
	}
}

/** Delete stored files; a file already gone is not an error. */
export async function offlineDelete(files: string[]): Promise<void> {
	await Promise.allSettled(files.map((file) => Filesystem.deleteFile({ path: at(file), directory: OFFLINE })));
}

/** The URL prefix the web view loads stored files from (same origin as the
 *  app: `capacitor://localhost/_capacitor_file_/…` on iOS,
 *  `https://localhost/_capacitor_file_/…` on Android, so CSP img-src 'self'
 *  admits it). Asked for at every launch — never persisted (see
 *  ./offlineFiles.ts). Null when the plugin cannot say. */
export async function offlineFileBase(): Promise<string | null> {
	try {
		const { uri } = await Filesystem.getUri({ path: ROOT, directory: OFFLINE });
		return Capacitor.convertFileSrc(uri).replace(/\/+$/, '');
	} catch {
		return null;
	}
}

export type AppShellHooks = {
	/** Client-side navigation (SvelteKit's `goto`). */
	navigate: (path: string) => unknown;
	/** Whether the reader is on the home page — Back there leaves the app. */
	isRoot: () => boolean;
	siteUrl: string;
};

/** SvelteKit's `data-sveltekit-reload` on the link or an ancestor (the
 *  cross-locale links): that page wants a full document load. */
const wantsReload = (a: Element) => {
	const v = a.closest('[data-sveltekit-reload]')?.getAttribute('data-sveltekit-reload');
	return v != null && v !== 'off';
};

let started = false;

export function startAppShell(hooks: AppShellHooks): void {
	if (started) return;
	started = true;

	// Links. On <body>, bubbling: after the components' own click handlers
	// (Svelte delegates them to the app's root element, inside <body>), so a
	// handler's preventDefault is respected here; and before SvelteKit's
	// router (on <html>), which leaves alone a click this has claimed.
	document.body.addEventListener('click', (e) => {
		if (!isPlainPrimaryClick(e)) return;
		const a = (e.target as Element | null)?.closest?.('a[href]');
		if (!(a instanceof HTMLAnchorElement)) return;
		const to = linkTarget(a.getAttribute('href')!, location.href, hooks.siteUrl, {
			download: a.hasAttribute('download'),
			newTab: !!a.target && a.target !== '_self'
		});
		if (!to) return;
		e.preventDefault();
		if (to.kind === 'external') void openExternal(to.url);
		else if (wantsReload(a)) location.assign(to.path);
		else hooks.navigate(to.path);
	});

	// Android's Back: close the topmost open overlay (each registers through
	// $lib/platform's onBack while open), else go back, else (home page, or
	// nothing to go back to) leave the app.
	void App.addListener('backButton', ({ canGoBack }) => {
		if (backStack.pop()) return;
		if (canGoBack && !hooks.isRoot()) history.back();
		else void App.exitApp();
	});

	// The launch splash stays up until the first frame of the reader is drawn
	// (capacitor.config.ts keeps a time limit as a safety net).
	requestAnimationFrame(() => {
		SplashScreen.hide().catch(() => {});
	});
}
