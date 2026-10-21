/**
 * The app's side of each $lib/platform function: Capacitor plugins. Loaded
 * only by index.ts behind `IS_APP` (a dynamic import of a build-time-dead
 * branch), so none of this — nor any @capacitor/* package — reaches the
 * website's bundle. ./web.ts is the website's side.
 */

import { App } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { Directory, Filesystem } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';
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

/** Status bar icons readable on the theme's ground. The ground itself is the
 *  page's own (the web view runs under the bar — app.css's status-bar strip);
 *  only an Android that still draws an opaque bar takes the colour too. */
export async function setStatusBar(color: string, dark: boolean): Promise<void> {
	try {
		await StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light });
		if (Capacitor.getPlatform() === 'android') await StatusBar.setBackgroundColor({ color });
	} catch {
		/* Not available here (Android 15+ is edge to edge): the strip covers it. */
	}
}

export type AppShellHooks = {
	/** Client-side navigation (SvelteKit's `goto`). */
	navigate: (path: string) => unknown;
	/** Whether the reader is on the home page — Back there leaves the app. */
	isRoot: () => boolean;
	siteUrl: string;
};

/** The open sheet / dialog / palette, if any — Back closes it first. */
const openOverlay = () => document.querySelector<HTMLElement>('[aria-modal="true"]');

export function startAppShell(hooks: AppShellHooks): void {
	// Links: decided before SvelteKit's router sees the click (capture phase);
	// preventDefault is what tells the router to leave it alone.
	document.addEventListener(
		'click',
		(e) => {
			if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
			const a = (e.target as Element | null)?.closest?.('a[href]');
			if (!(a instanceof HTMLAnchorElement)) return;
			const to = linkTarget(a.getAttribute('href')!, location.href, hooks.siteUrl, a.hasAttribute('download'));
			if (!to) return;
			e.preventDefault();
			if (to.kind === 'internal') hooks.navigate(to.path);
			else void openExternal(to.url);
		},
		{ capture: true }
	);

	// Android's Back: close what is open, else go back, else (home page, or
	// nothing to go back to) leave the app. An overlay that ignores Escape
	// gets one press, then Back navigates as usual.
	let lastOverlay: HTMLElement | null = null;
	void App.addListener('backButton', ({ canGoBack }) => {
		const overlay = openOverlay();
		if (overlay && overlay !== lastOverlay) {
			lastOverlay = overlay;
			(document.activeElement ?? document.body).dispatchEvent(
				new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
			);
			return;
		}
		lastOverlay = null;
		if (canGoBack && !hooks.isRoot()) history.back();
		else void App.exitApp();
	});

	// The launch splash stays up until the first frame of the reader is drawn
	// (capacitor.config.ts keeps a time limit as a safety net).
	requestAnimationFrame(() => void SplashScreen.hide().catch(() => {}));
}
