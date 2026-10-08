import { building } from '$app/environment';
import { AUDIENCE_HUBS, type AudienceHubConfig } from './audienceHub';
import {
	getAudienceShelf,
	listAudienceLanguages,
	type AudienceShelf,
	type HubAudience
} from './library-public';
import { getLang } from './lang.svelte';

/** An empty shelf — what a failed load renders behind its Try again. */
export const emptyShelf = (): AudienceShelf => ({
	series: [],
	people: [],
	editions: [],
	more: [],
	plans: [],
	topic: null,
	start: null,
	printable: [],
	languages: []
});

/**
 * Both hub routes' `load`. Caught, not thrown — the `loadShelf` rule: a lagging
 * API must not fail the prerender, and the page reports the failure with Try
 * again rather than claiming an empty shelf.
 */
export const hubLoad =
	(hub: AudienceHubConfig) =>
	async ({ fetch }: { fetch: typeof globalThis.fetch }) => {
		try {
			return { hub, shelf: await getAudienceShelf(hub.audience, getLang(), fetch), loadError: false };
		} catch {
			return { hub, shelf: emptyShelf(), loadError: true };
		}
	};

let built: Promise<Record<HubAudience, string[]>> | null = null;

/**
 * Which languages each hub has something in — the home snapshot's hub links
 * and the sitemap, both build-time readers. Language-independent, so the
 * build asks once for every locale (memoized only while building: neither
 * reader's response is inlined into a page). Every hub gets a list, empty
 * when the call fails or the API doesn't name it yet — both readers are
 * decoration and must never take their page down.
 */
export function hubLanguages(): Promise<Record<HubAudience, string[]>> {
	const ask = () =>
		listAudienceLanguages()
			.catch(() => ({}) as Partial<Record<HubAudience, string[]>>)
			.then(
				(got) =>
					Object.fromEntries(AUDIENCE_HUBS.map((h) => [h.audience, got[h.audience] ?? []])) as Record<
						HubAudience,
						string[]
					>
			);
	if (!building) return ask();
	return (built ??= ask());
}
