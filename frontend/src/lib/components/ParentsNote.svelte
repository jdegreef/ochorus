<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * The note for the adult choosing for a child — under /series' "For young
	 * readers" group, and closing each young-reader hub. A bordered box (not the
	 * read card's tint): it is set aside for the adult, not part of the shelf.
	 * An `<aside>` named by `labelledby` where it sits beside the shelf's cards;
	 * a plain box where a section heading already names it.
	 */
	let {
		labelledby,
		class: klass = '',
		children
	}: { labelledby?: string; class?: string; children: Snippet } = $props();
</script>

{#if labelledby}
	<aside class="parents-note {klass}" aria-labelledby={labelledby}>{@render children()}</aside>
{:else}
	<div class="parents-note {klass}">{@render children()}</div>
{/if}

<style>
	.parents-note {
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		padding: 0.85rem 1rem;
	}
</style>
