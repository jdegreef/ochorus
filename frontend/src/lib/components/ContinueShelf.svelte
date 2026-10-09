<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * "Pick up where you left off" on a shelf — Books' Continue reading, Plans'
	 * Continue your plans, Series' Continue your series. One heading treatment,
	 * one grid of `<ContinueRow>`s, one place on the page: between the header
	 * and the filter bar, hidden while the reader is filtering (the caller's
	 * `{#if}`). Each shelf keeps its own heading words.
	 */
	let { heading, children }: { heading: string; children: Snippet } = $props();
</script>

<section class="mb-8">
	<h2 class="section-label mb-4">{heading}</h2>
	<!-- grid-cols-1, not the implicit track: a row's truncating title has a
	     min-content width that otherwise widens a phone's column off-screen. -->
	<ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
		{@render children()}
	</ul>
</section>
