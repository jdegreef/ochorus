import { appOfflineReady } from '$lib/appOffline.svelte';
import { IS_APP } from '$lib/platform';

// Public pages are prerendered to static HTML at build time for SEO (the load
// functions fetch from the API during the build). The reader and search opt out
// (prerender=false + ssr=false) and run as a client-side SPA.
export const prerender = true;

// The app's downloaded books: where their saved images are served this launch,
// resolved before the first page draws, so a downloaded cover never tries the
// network first and gets marked broken offline ($lib/appOffline). Capped, and
// never fails. The website has no load here (`IS_APP` is a build-time constant).
export const load = IS_APP ? () => appOfflineReady() : undefined;
