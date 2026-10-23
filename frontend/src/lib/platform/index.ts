/**
 * The native-app seam: the ONE place the reader learns whether it is running
 * as the website or inside the iOS / Android app (Capacitor), and the one
 * place that talks to Capacitor. Everything else asks this module.
 *
 * Each function has a web side (./web.ts, browser APIs) and an app side
 * (./native.ts, Capacitor plugins). The app side is a dynamic import behind
 * `IS_APP`, a build-time constant, so the website's bundle carries neither it
 * nor any @capacitor/* code.
 *
 * eslint.config.js forbids `@capacitor/*` imports outside src/lib/platform/, so
 * an app-only dependency can't leak into a website code path by accident.
 * See frontend/MOBILE.md for how the app is built and run.
 */

import * as web from './web';
import { backStack } from './back';
import type { AppShellHooks } from './native';
import type { ShareData, ShareResult } from './web';

export type { ShareData, ShareResult, AppShellHooks };

/**
 * True in the app's bundle, false on the website. A build-time constant
 * (`__APP__`, set by scripts/build-app.mjs), so the website ships none of the
 * app-only branches.
 */
export const IS_APP: boolean = __APP__;

/**
 * The website origin (e.g. `https://ochorus.com`) the app loads the images it
 * does not bundle from — read only by `$lib/assetUrl`. '' on the website. A
 * build-time constant (`__APP_ASSET_ORIGIN__`, vite.config.ts) from the same
 * reading of PUBLIC_SITE_URL that the app's CSP img-src admits.
 */
export const APP_ASSET_ORIGIN: string = __APP_ASSET_ORIGIN__;

const native = () => import('./native');

/** Whether `share` opens an OS share sheet here: always in the app, and in
 *  a browser whose sheet works (not desktop Chromium — see web.ts). */
export function canShare(): boolean {
	return IS_APP || web.canShare();
}

/**
 * Register what Android's Back button should close while an overlay (sheet,
 * dialog, menu, popover) is open; returns the unregister, to call on close.
 * Back closes the most recently opened one before it navigates. Nothing on
 * the website, which has no Back button to answer.
 */
export function onBack(close: () => void): () => void {
	return IS_APP ? backStack.push(close) : () => {};
}

/** The OS share sheet. `aborted` = the reader dismissed it (do nothing);
 *  `unavailable` = no sheet, or it failed (offer another way). */
export async function share(data: ShareData): Promise<ShareResult> {
	return IS_APP ? (await native()).share(data) : web.share(data);
}

/** Share a file (an image card) through the OS sheet. `unavailable` means the
 *  caller should fall back (a download, on the website). */
export async function shareFile(blob: Blob, filename: string, text: string): Promise<ShareResult> {
	return IS_APP ? (await native()).shareFile(blob, filename, text) : web.shareFile(blob, filename, text);
}

/** Open a URL outside the reader: the system's browser in the app, a new tab
 *  on the website. */
export async function openExternal(url: string): Promise<void> {
	return IS_APP ? (await native()).openExternal(url) : web.openExternal(url);
}

/** Match the phone's status bar to the theme (`color` = the theme's ground).
 *  The website's equivalent is <meta name="theme-color">, so nothing here. */
export async function setStatusBar(color: string, dark: boolean): Promise<void> {
	if (IS_APP) await (await native()).setStatusBar(color, dark);
}

/**
 * The app's shell, once, from the root layout: marks <html data-app> (app.css
 * keeps the page clear of the notch / status bar under it), sends outside
 * links and website-only files to the system browser, wires Android's Back
 * button, and lifts the launch splash. Nothing on the website.
 */
export function startAppShell(hooks: AppShellHooks): void {
	if (!IS_APP) return;
	document.documentElement.setAttribute('data-app', '');
	void native().then((n) => n.startAppShell(hooks));
}

/*
 * The app's downloaded books ("Download for offline") on the phone's own
 * storage — the app runs no service worker, so its downloads cannot live in
 * the Cache API as the website's do. `file` is a path inside the app's
 * offline folder (./offlineFiles.ts says which); $lib/offlineBooks writes
 * them, $lib/appOffline reads them. Nothing is stored on the website.
 */

/** A downloaded API response, or null when there is none. */
export async function offlineReadText(file: string): Promise<string | null> {
	return IS_APP ? (await native()).offlineReadText(file) : web.offlineReadText(file);
}

/** Store a downloaded API response; whether it was written. */
export async function offlineWriteText(file: string, text: string): Promise<boolean> {
	return IS_APP ? (await native()).offlineWriteText(file, text) : web.offlineWriteText(file, text);
}

/** Download `url` (an image on the website) into `file`; whether it arrived. */
export async function offlineSaveFile(file: string, url: string): Promise<boolean> {
	return IS_APP ? (await native()).offlineSaveFile(file, url) : web.offlineSaveFile(file, url);
}

/** Delete downloaded files. */
export async function offlineDelete(files: string[]): Promise<void> {
	return IS_APP ? (await native()).offlineDelete(files) : web.offlineDelete(files);
}

/** The URL the stored files are served under this launch (see
 *  ./offlineFiles.ts — resolved each time, never persisted). */
export async function offlineFileBase(): Promise<string | null> {
	return IS_APP ? (await native()).offlineFileBase() : web.offlineFileBase();
}
