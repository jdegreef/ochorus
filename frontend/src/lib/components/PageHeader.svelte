<script lang="ts">
	import type { Snippet } from 'svelte';
	import Fleuron from '$lib/components/Fleuron.svelte';
	import { sectionDest, type NavSection } from '$lib/contentNav';
	import { hydrateSrc } from '$lib/hydrateSrc';

	/**
	 * The standard header for a top-level browse page (Books, Topics, Plans,
	 * Sermons, Biographies, Search) and for the app pages (Settings, Notebook) —
	 * `pageShell.test.ts` requires it on both lists, so a change here moves them all.
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
	 *
	 * A library section's own page passes `section`: its emblem then sits beside
	 * the title in the section's hue, and the ornament under it is the
	 * section's device rather than the house leaf. Both are static files under
	 * /marks/, fetched by these pages alone.
	 */
	let {
		eyebrow = '',
		title,
		tagline = '',
		meta,
		section
	}: {
		/** Optional kicker above the title, e.g. "SERMONS". Rendered uppercase. */
		eyebrow?: string;
		/** The page title — goes in the <h1>. */
		title: string;
		/** One-line description under the title. */
		tagline?: string;
		/** Optional counts line ("59 books · 27 authors"). */
		meta?: Snippet;
		/** The library section this page is the shelf of, if any. */
		section?: NavSection;
	} = $props();

</script>

<header class="mb-8">
	{#if eyebrow}
		<p class="eyebrow mb-2 text-accent">{eyebrow}</p>
	{/if}
	{#if section}
		<div class="mb-3 flex items-center gap-3">
			<span class="emblem-chip page-header-emblem" data-section={section}>
				<img
					src="/marks/emblem-{section}.svg"
					alt=""
					width="29"
					height="29"
					use:hydrateSrc={{ src: `/marks/emblem-${section}.svg` }}
				/>
			</span>
			<h1 class="text-h1">{title}</h1>
		</div>
	{:else}
		<h1 class="text-h1 mb-3">{title}</h1>
	{/if}
	<div class="mb-3"><Fleuron ornament={section && sectionDest(section).ornament} /></div>
	{#if tagline}
		<p class="max-w-2xl text-body text-muted">{tagline}</p>
	{/if}
	{#if meta}
		<p class="mt-1 text-small text-muted">{@render meta()}</p>
	{/if}
</header>
