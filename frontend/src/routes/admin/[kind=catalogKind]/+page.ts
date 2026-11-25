// Admin inventory list — authenticated, live data.
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = ({ params }) => ({ kind: params.kind });
