// Admin language drill-down: authenticated, live data — client-side SPA route.
export const prerender = false;
export const ssr = false;

export const load = ({ params }: { params: { code: string } }) => ({ code: params.code });
