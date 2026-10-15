/**
 * Whether this build is the native app's (iOS + Android, via Capacitor) rather
 * than the website's. scripts/build-app.mjs sets OCHORUS_TARGET=app; the one
 * definition, read by svelte.config.js (what to build) and vite.config.ts (the
 * `__APP__` constant behind `IS_APP`, and the app-only plugin). See MOBILE.md.
 */
export const APP = process.env.OCHORUS_TARGET === 'app';
