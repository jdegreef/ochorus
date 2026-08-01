<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * The standard header for a top-level browse page (Books, Topics, Plans,
	 * Sermons, Biographies, Search).
	 *
	 * These six had drifted into six different headers: `text-display` on four
	 * of them but `text-h1` on Plans and Search, bottom margins of mb-2/mb-3,
	 * header margins of mb-5/mb-6/mb-8, an eyebrow on Sermons only, and a
	 * tagline measure that was capped on some pages and not others. None of it
	 * was deliberate.
	 *
	 * The type scale reserves `.text-display` for the hero (see STYLE_GUIDE §2),
	 * so page titles are `.text-h1` — the home hero keeps display, and is the
	 * only place that should.
	 */
	let {
		eyebrow = '',
		title,
		tagline = '',
		meta
	}: {
		/** Optional kicker above the title, e.g. "SERMONS". Rendered uppercase. */
		eyebrow?: string;
		/** The page title — goes in the <h1>. */
		title: string;
		/** One-line description under the title. */
		tagline?: string;
		/** Optional counts line ("59 books · 27 authors"). */
		meta?: Snippet;
	} = $props();
</script>

<header class="mb-8">
	{#if eyebrow}
		<p class="mb-2 text-eyebrow font-semibold uppercase tracking-widest text-accent">{eyebrow}</p>
	{/if}
	<h1 class="text-h1 mb-2">{title}</h1>
	{#if tagline}
		<p class="max-w-2xl text-body text-muted">{tagline}</p>
	{/if}
	{#if meta}
		<p class="mt-1 text-small text-muted">{@render meta()}</p>
	{/if}
</header>
