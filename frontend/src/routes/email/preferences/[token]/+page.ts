// The email preference center opens from an unguessable token in an email
// footer — account- and token-specific, nothing to prerender or crawl. Client
// only; the page fetches its own state. The token only travels to the API, so
// it's handed to the component rather than loaded here.
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = ({ params }) => ({ token: params.token });
