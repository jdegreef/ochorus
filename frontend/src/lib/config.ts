import { PUBLIC_API_BASE_URL } from '$env/static/public';
import { env } from '$env/dynamic/public';

// Base URL of the Django API. Empty string = same origin (production, where the
// API is served from the same host). In dev, set PUBLIC_API_BASE_URL to the
// local backend (see .env).
export const API_BASE_URL = PUBLIC_API_BASE_URL || '';

// Public site origin, used to build absolute canonical / Open Graph / sitemap
// URLs at prerender time. Set PUBLIC_SITE_URL per deployment; falls back to the
// current Render URL (update it when the site moves to ochorus.com).
export const SITE_URL = (env.PUBLIC_SITE_URL || 'https://ochorus-web.onrender.com').replace(
	/\/+$/,
	''
);

// Where readers can reach the ministry. An existing mailbox, not a new one:
// DEPLOYMENT.md §5 warns against touching the MX/TXT records because they carry
// mail for this address. Overridable per deployment so a future forwarding
// address is a config change, not a code change.
export const CONTACT_EMAIL = env.PUBLIC_CONTACT_EMAIL || 'support@ochorus.com';
