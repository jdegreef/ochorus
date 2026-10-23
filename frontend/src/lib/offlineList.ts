import { readJSON } from './persisted';

/**
 * The list of downloaded book editions ("Download for offline"), in
 * localStorage. $lib/offlineBooks owns it (downloads, removes); this module is
 * only its shape and its read, so $lib/appOffline can index it without
 * importing the downloader.
 */
export const OFFLINE_BOOKS_KEY = 'ochorus:offline-books';

export interface OfflineBook {
	slug: string;
	title: string;
	author: string;
	coverUrl: string;
	language: string;
	chapterCount: number;
	at: number;
	/**
	 * App only: the API paths (path + query, exactly as $lib/api requests them)
	 * and the site image paths this download stored on the phone — what
	 * $lib/appOffline serves, and what `remove()` deletes. The website's
	 * downloads live in the Cache API and record neither, so both are optional
	 * and every existing entry still reads.
	 */
	apiKeys?: string[];
	images?: string[];
}

export function readOfflineList(): OfflineBook[] {
	const raw = readJSON<OfflineBook[]>(OFFLINE_BOOKS_KEY, []);
	return Array.isArray(raw) ? raw : [];
}

/** The downloads as the reader sees them listed: newest first. */
export const newestFirst = (list: OfflineBook[]): OfflineBook[] => [...list].sort((a, b) => b.at - a.at);
