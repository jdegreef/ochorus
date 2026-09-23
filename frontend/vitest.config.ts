import { fileURLToPath } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defaultClientConditions } from 'vite';
import { defineConfig } from 'vitest/config';

/**
 * Unit-test config for the reader's pure logic and localStorage stores.
 *
 * We use the plain Svelte plugin (not the full SvelteKit plugin) so `.svelte.ts`
 * rune modules compile, and alias the SvelteKit imports the stores use:
 * `$app/environment` → a tiny browser=true mock, `$app/navigation` → a stub
 * that records what was preloaded, and `$lib` → `src/lib`. The jsdom
 * environment supplies `localStorage`, which the stores persist to.
 */
export default defineConfig({
	plugins: [svelte({ compilerOptions: { runes: true } })],
	resolve: {
		// The plugin compiles components for the CLIENT, so `svelte` itself has to
		// resolve to its browser entry too — without this, `mount()` comes from
		// index-server.js and a component test dies inside Svelte's internals
		// rather than in the assertion you wrote.
		//
		// Spread rather than `['browser']`: Vite REPLACES its defaults with what
		// this names, so the bare form silently drops `module` and
		// `development|production` and leaves a future dependency free to resolve
		// to a legacy build.
		conditions: [...defaultClientConditions],
		alias: [
			{
				find: '$app/environment',
				replacement: fileURLToPath(new URL('./src/test/app-environment.ts', import.meta.url))
			},
			{
				find: '$app/navigation',
				replacement: fileURLToPath(new URL('./src/test/app-navigation.ts', import.meta.url))
			},
			{
				find: /^\$env\/(static|dynamic)\/public$/,
				replacement: fileURLToPath(new URL('./src/test/env-public.ts', import.meta.url))
			},
			{
				find: /^\$lib\/(.*)$/,
				replacement: fileURLToPath(new URL('./src/lib/', import.meta.url)) + '$1'
			},
			{ find: '$lib', replacement: fileURLToPath(new URL('./src/lib', import.meta.url)) }
		]
	},
	// The build-time constants vite.config.ts injects, fixed for tests.
	define: { __COVERS_VERSION__: JSON.stringify('test-covers') },
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		globals: true,
		// Runs before the assertions in every file, and stops the run with one
		// message when the environment cannot do what these tests need. A broken
		// jsdom localStorage otherwise surfaces as ~99 unrelated-looking failures
		// in files nobody touched — noise that reads as "broken here" and hides
		// any real regression underneath it. See the file for the mechanism.
		setupFiles: [fileURLToPath(new URL('./src/test/dom-environment-guard.ts', import.meta.url))]
	}
});
