<script lang="ts">
	import { quoteRuns } from '$lib/quoteText';

	// A quotation's text with the extraction's flattened typography repaired —
	// em dashes, and divine names back in small caps (see $lib/quoteText). Shared
	// by the quote card and the /quotes index so a line reads the same in both.
	let { text }: { text: string } = $props();
	const runs = $derived(quoteRuns(text));
</script>

<!-- One line on purpose: whitespace between the {#each} tags would print. -->
{#each runs as r, i (i)}{#if r.smallCaps}<span class="sc">{r.text}</span>{:else}{r.text}{/if}{/each}

<style>
	.sc {
		font-variant-caps: small-caps;
	}
</style>
