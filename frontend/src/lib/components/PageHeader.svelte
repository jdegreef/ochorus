<script lang="ts">
	import type { Snippet } from 'svelte';

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
	 * Plain on purpose (design review #4, 2026-11-06): the title, one sentence,
	 * and the shelf's size at the end of that sentence in the same muted run.
	 * The section emblem beside the title and the ornament under it are gone —
	 * they were decoration in front of content, the same on every shelf, and
	 * made each page read as a template. Don't add a device back here.
	 */
	let {
		eyebrow = '',
		title,
		tagline = '',
		meta,
		srOnly = false
	}: {
		/** Optional kicker above the title, e.g. "SERMONS". Rendered uppercase. */
		eyebrow?: string;
		/** The page title — goes in the <h1>. */
		title: string;
		/** One-line description under the title. */
		tagline?: string;
		/** Optional counts ("428 sermons · 38 preachers"), run on after the tagline. */
		meta?: Snippet;
		/**
		 * Keep the h1 for screen readers and the outline, but draw nothing — for
		 * a page whose first control IS its header (Search: the field is the
		 * header, design review #25). Tagline and meta are dropped with it.
		 */
		srOnly?: boolean;
	} = $props();
</script>

{#if srOnly}
	<h1 class="sr-only">{title}</h1>
{:else}
	<header class="mb-8">
		{#if eyebrow}
			<p class="eyebrow mb-2 text-accent">{eyebrow}</p>
		{/if}
		<h1 class="text-h1 mb-2">{title}</h1>
		{#if tagline || meta}
			<p class="max-w-2xl text-body text-muted">
				{#if tagline}{tagline}{#if meta}{' '}{/if}{/if}{#if meta}<span class="page-header-count"
						>{@render meta()}</span
					>{/if}
			</p>
		{/if}
	</header>
{/if}

<style>
	/* The count runs on after the sentence and drops to the next line whole
	   ("428 sermons · 38 preachers") rather than splitting across two; only a
	   count longer than the line itself wraps inside. */
	.page-header-count {
		display: inline-block;
	}
</style>
