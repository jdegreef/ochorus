import { getLang } from '$lib/lang.svelte';
import { hubEntries, loadHub } from '$lib/hubs';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to tradition/<slug>/index.html, served as a
// directory index by the static host (see authors/[slug] for the full note).
export const trailingSlash = 'always';

export const entries: EntryGenerator = () => hubEntries('tradition');

export const load: PageLoad = ({ params, fetch }) => loadHub('tradition', params.slug, getLang(), fetch);
