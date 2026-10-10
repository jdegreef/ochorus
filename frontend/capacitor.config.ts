import type { CapacitorConfig } from '@capacitor/cli';

/**
 * The native app shell (iOS + Android). It bundles build-app/ — the reader built
 * by scripts/build-app.mjs — and serves it from inside the app; content comes
 * from the live API like any client-side navigation. See MOBILE.md.
 *
 * appId is permanent: it is the app's identity in both stores and in every
 * signing certificate and deep-link file. Never change it after the first
 * store upload.
 */
const config: CapacitorConfig = {
	appId: 'com.ochorus.app',
	appName: 'Ochorus',
	webDir: 'build-app',
	// The reader's cream paper, so the frame behind the web view never flashes
	// white on launch or overscroll (manifest.json's background_color).
	backgroundColor: '#faf6ef'
};

export default config;
