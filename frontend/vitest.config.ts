import { fileURLToPath } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

/**
 * Unit-test config for the reader's pure logic and localStorage stores.
 *
 * We use the plain Svelte plugin (not the full SvelteKit plugin) so `.svelte.ts`
 * rune modules compile, and alias the two SvelteKit imports the stores use:
 * `$app/environment` → a tiny browser=true mock, and `$lib` → `src/lib`. The
 * jsdom environment supplies `localStorage`, which the stores persist to.
 */
export default defineConfig({
	plugins: [svelte({ compilerOptions: { runes: true } })],
	resolve: {
		alias: [
			{
				find: '$app/environment',
				replacement: fileURLToPath(new URL('./src/test/app-environment.ts', import.meta.url))
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
