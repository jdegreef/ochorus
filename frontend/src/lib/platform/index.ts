/**
 * The native-app seam: the ONE place the reader learns whether it is running
 * as the website or inside the iOS / Android app (Capacitor), and — as the app
 * grows native features (share sheet, deep links, offline files, sign-in) —
 * the one place that talks to Capacitor. Everything else asks this module.
 *
 * eslint.config.js forbids `@capacitor/*` imports outside src/lib/platform/, so
 * an app-only dependency can't leak into a website code path by accident.
 * See frontend/MOBILE.md for how the app is built and run.
 */

/**
 * True in the app's bundle, false on the website. A build-time constant
 * (`__APP__`, set by scripts/build-app.mjs), so the website ships none of the
 * app-only branches.
 */
export const IS_APP: boolean = __APP__;

/**
 * The website origin (e.g. `https://ochorus.com`) the app loads the images it
 * does not bundle from — read only by `$lib/assetUrl`. '' on the website. A
 * build-time constant (`__APP_ASSET_ORIGIN__`, vite.config.ts) from the same
 * reading of PUBLIC_SITE_URL that the app's CSP img-src admits.
 */
export const APP_ASSET_ORIGIN: string = __APP_ASSET_ORIGIN__;
