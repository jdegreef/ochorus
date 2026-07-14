/**
 * Test stand-in for SvelteKit's `$app/environment`. The stores guard localStorage
 * access with `browser`; in jsdom we want it truthy so the persistence paths run.
 */
export const browser = true;
export const dev = false;
export const building = false;
export const version = 'test';
