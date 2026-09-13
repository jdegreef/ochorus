// Admin per-sermon detail: authenticated, live data — SPA route.
export const prerender = false;
export const ssr = false;

export const load = ({ params }: { params: { slug: string } }) => ({ slug: params.slug });
