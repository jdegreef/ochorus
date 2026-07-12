// The admin dashboard is authenticated and shows live data — keep it a
// client-side SPA route (never prerendered, no SSR), and load the stats in the
// component so it can react to sign-in state.
export const prerender = false;
export const ssr = false;
