// Admin automated-email editor: authenticated, live data — SPA route.
export const prerender = false;
export const ssr = false;

export const load = ({ params }: { params: { step: string } }) => ({ step: params.step });
