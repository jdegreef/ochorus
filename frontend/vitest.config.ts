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
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		globals: true
	}
});
