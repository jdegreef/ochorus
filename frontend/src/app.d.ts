// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}

	/**
	 * The commit this bundle was built from — injected by `define` in
	 * vite.config.ts. Empty outside a Render build.
	 */
	const __RELEASE__: string;

	/**
	 * True in the native app's bundle (scripts/build-app.mjs) — injected by
	 * `define` in vite.config.ts. Read it as `IS_APP` from $lib/platform.
	 */
	const __APP__: boolean;
}

export {};
