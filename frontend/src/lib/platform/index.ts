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
