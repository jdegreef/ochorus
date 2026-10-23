/**
 * The website's side of each $lib/platform function: plain browser APIs. The
 * app's side is ./native.ts. index.ts picks one by `IS_APP`.
 */

export type ShareResult = 'shared' | 'aborted' | 'unavailable';
export type ShareData = { title?: string; text?: string; url?: string };

/** Whether the browser has a share sheet worth opening. Not on desktop
 *  Chromium (the only engine with `userAgentData`, here with a fine pointer):
 *  Chrome and Edge there hand off to a system dialog that often shows nothing
 *  — a click that "does nothing". Phones and Safari keep the OS sheet. */
export function canShare(): boolean {
	return (
		typeof navigator !== 'undefined' &&
		typeof navigator.share === 'function' &&
		!('userAgentData' in navigator && !window.matchMedia?.('(pointer: coarse)').matches)
	);
}

/** The OS share sheet via the Web Share API. `aborted` = dismissed by the
 *  reader; `unavailable` = no sheet here, or it failed for another reason. */
export async function share(data: ShareData): Promise<ShareResult> {
	if (!canShare()) return 'unavailable';
	try {
		await navigator.share(data);
		return 'shared';
	} catch (err) {
		return (err as Error)?.name === 'AbortError' ? 'aborted' : 'unavailable';
	}
}

/** Share a file (a rendered quote card) where the browser can. */
export async function shareFile(blob: Blob, filename: string, text: string): Promise<ShareResult> {
	if (typeof navigator === 'undefined' || typeof File === 'undefined') return 'unavailable';
	const file = new File([blob], filename, { type: blob.type || 'application/octet-stream' });
	const nav = navigator as Navigator & { canShare?: (data?: { files?: File[] }) => boolean };
	if (!nav.canShare?.({ files: [file] })) return 'unavailable';
	try {
		await navigator.share({ files: [file], text });
		return 'shared';
	} catch (err) {
		return (err as Error)?.name === 'AbortError' ? 'aborted' : 'unavailable';
	}
}

/** A new tab — the website's "somewhere else". */
export async function openExternal(url: string): Promise<void> {
	window.open(url, '_blank', 'noopener,noreferrer');
}

/*
 * Downloaded books' files on the phone (native.ts). The website keeps its
 * downloads in the Cache API, served by the service worker
 * ($lib/offlineBooks), so it stores nothing here.
 */
export async function offlineReadText(_file: string): Promise<string | null> {
	return null;
}
export async function offlineWriteText(_file: string, _text: string): Promise<boolean> {
	return false;
}
export async function offlineSaveFile(_file: string, _url: string): Promise<boolean> {
	return false;
}
export async function offlineDelete(_files: string[]): Promise<void> {}
export async function offlineFileBase(): Promise<string | null> {
	return null;
}
