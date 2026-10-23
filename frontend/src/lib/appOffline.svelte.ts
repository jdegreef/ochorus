/**
 * Reading a downloaded book in the native app, with no connection.
 *
 * The website reads its downloads through the service worker, which answers
 * `/api/library/…` and images from the `ochorus-offline` cache before the
 * network. The app has no service worker (iOS's app web view runs none), so it
 * stores a download on the phone ($lib/platform's offline files) and answers
 * from it here, at the two places the reader asks for things:
 *
 * - **API reads**: `$lib/api` asks `readDownloaded` before the network, for a
 *   public library GET only. A path in the downloaded set (the edition's book
 *   and chapter responses, recorded as `apiKeys` in the metadata list) is
 *   answered from its stored copy, which is refreshed in the background when
 *   online — the service worker's offlineThenSWR. The set is indexed
 *   synchronously from that list, so a path nobody downloaded costs a Set
 *   lookup and nothing else.
 * - **Images**: `$lib/assetUrl` asks `localAsset` for a site path. A saved one
 *   (cover, its variants, chapter illustrations — `images` in the metadata)
 *   gets its file's URL in the app; anything else loads from the website as
 *   before. The map is `$state`, so a cover re-renders when its book is
 *   downloaded or removed.
 *
 * The files' base URL is resolved once per launch (`appOfflineReady`, awaited
 * by the root layout's load before the first render, so a cover never tries
 * the network first and is marked broken offline). Nothing here runs on the
 * website: every entry point checks `IS_APP`, a build-time constant.
 */
import { browser } from '$app/environment';
import { API_BASE_URL } from './config';
import { readOfflineList, type OfflineBook } from './offlineList';
import { IS_APP, offlineFileBase, offlineReadText, offlineWriteText } from './platform';
import { apiFile, imageFile, offlineFileUrl } from './platform/offlineFiles';

// No module-level state that runs code on import: the website's bundle drops
// this module whole (every caller is behind IS_APP), which a top-level
// `$state` or `new` would prevent.
class LocalImages {
	/** Site path → the saved file's URL. */
	urls = $state<Record<string, string>>({});
}
let images: LocalImages | undefined;
let base: string | null = null;
let ready: Promise<void> | undefined;
let apiKeys: Set<string> | undefined;

const downloadedApi = () => (apiKeys ??= new Set(readOfflineList().flatMap((b) => b.apiKeys ?? [])));

function mapImages(list: OfflineBook[]) {
	if (!images || !base) return;
	const urls: Record<string, string> = {};
	for (const b of list) {
		for (const path of b.images ?? []) {
			const file = imageFile(path);
			if (file) urls[path] = offlineFileUrl(base, file);
		}
	}
	images.urls = urls;
}

/** Resolve where the saved files are served this launch and map the saved
 *  images. Once; never rejects; capped so a silent bridge cannot hold the
 *  launch (images then load from the website until the answer comes). */
export function appOfflineReady(): Promise<void> {
	if (!IS_APP || !browser) return Promise.resolve();
	images ??= new LocalImages();
	ready ??= offlineFileBase()
		.then((b) => {
			base = b;
			mapImages(readOfflineList());
		})
		.catch(() => {});
	return Promise.race([ready, new Promise<void>((resolve) => setTimeout(resolve, 1500))]);
}

/** After the metadata list changed (a download or a removal): re-index. */
export function reindexOffline(list: OfflineBook[]): void {
	if (!IS_APP) return;
	apiKeys = new Set(list.flatMap((b) => b.apiKeys ?? []));
	mapImages(list);
}

/** The saved file's URL for a site image path, when it was downloaded. */
export function localAsset(path: string): string | undefined {
	return images?.urls[path];
}

/**
 * A downloaded API response for `path` (path + query, as $lib/api requests
 * it), parsed — or undefined, and the caller asks the network as usual. The
 * caller only asks for public library GETs.
 */
export async function readDownloaded(path: string): Promise<unknown> {
	if (!IS_APP || !downloadedApi().has(path)) return undefined;
	const text = await offlineReadText(apiFile(path));
	if (text == null) return undefined;
	let data: unknown;
	try {
		data = JSON.parse(text);
	} catch {
		return undefined;
	}
	if (navigator.onLine) void refresh(path);
	return data;
}

/** Bring a stored copy up to date; never fatal, and never re-stores a path
 *  whose edition was removed while the request was out. */
async function refresh(path: string): Promise<void> {
	try {
		const res = await fetch(`${API_BASE_URL}${path}`);
		if (!res.ok) return;
		const text = await res.text();
		JSON.parse(text);
		if (downloadedApi().has(path)) await offlineWriteText(apiFile(path), text);
	} catch {
		/* offline after all, or a bad body — keep the copy we have */
	}
}
