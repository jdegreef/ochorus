// Admin automation builder: authenticated, live data — SPA route.
export const prerender = false;
export const ssr = false;

export const load = ({ params }: { params: { id: string } }) => ({ id: Number(params.id) });
