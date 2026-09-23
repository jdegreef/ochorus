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
	 * The day this bundle was built (whole days since the epoch) — injected by
	 * `define` in vite.config.ts. Seeds the home page's per-deploy picks.
	 */
	const __BUILD_DAY__: number;
}

export {};
