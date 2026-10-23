import { homeShelves, type HomeShelves } from '$lib/homeShelves';
import { IS_APP } from '$lib/platform';

/** The app's derivations, one per language per session: home and About share
 *  one round of list requests instead of five each. A failed one is forgotten. */
const derived = new Map<string, Promise<HomeShelves>>();

/**
 * The build's home snapshot for `lang`, read through the caller's SvelteKit
 * `fetch` so the response is inlined into the prerendered HTML and REPLAYED at
 * hydration. The home page shows its shelves and counts from it; About shows
 * the same counts, so the two can never state different library totals.
 *
 * On the web it throws when the file can't be read — each caller decides how
 * loud. The app prerenders nothing, so it has no snapshot file: it derives the
 * shelves from the live API as the snapshot's own endpoint does at build
 * (routes/home-shelves), where a failed list comes back EMPTY rather than
 * throwing — so a caller treats a zero count as nothing to show.
 */
export async function readHomeSnapshot(fetch: typeof globalThis.fetch, lang: string): Promise<HomeShelves> {
	if (IS_APP) {
		let once = derived.get(lang);
		if (!once) {
			once = homeShelves(lang);
			derived.set(lang, once);
			once.catch(() => derived.delete(lang));
		}
		return once;
	}
	const res = await fetch(`/home-shelves/${lang}.json`);
	if (!res.ok) throw new Error(`home shelves: ${res.status}`);
	return (await res.json()) as HomeShelves;
}
