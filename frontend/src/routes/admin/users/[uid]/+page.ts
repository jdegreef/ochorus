// Admin per-user detail: authenticated, live data — client-side SPA route.
export const prerender = false;
export const ssr = false;

export const load = ({ params }: { params: { uid: string } }) => ({ uid: params.uid });
