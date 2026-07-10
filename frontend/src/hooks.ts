import type { Reroute } from '@sveltejs/kit';
import { deLocalizeUrl } from '$lib/paraglide/runtime';

// Map a localized URL (e.g. /es/biographies) back to the canonical route
// (/biographies) so the same +page.svelte serves every language. The active
// locale is read from the URL by the Paraglide runtime.
export const reroute: Reroute = ({ url }) => deLocalizeUrl(url).pathname;
