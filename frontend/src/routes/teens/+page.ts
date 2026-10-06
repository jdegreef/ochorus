import { TEENS_HUB } from '$lib/audienceHub';
import { hubLoad } from '$lib/audienceHubData';

// A young-reader hub ($lib/audienceHub) — a browse shelf on the /series model.
// Prerenders to /teens/index.html, so its links carry the slash (href.ts
// isSlashedPath) and the crawler reaches every localized copy from the footer.
export const prerender = true;
export const trailingSlash = 'always';

export const load = hubLoad(TEENS_HUB);
