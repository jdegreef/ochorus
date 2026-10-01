<script lang="ts">
	import type { Trend } from '$lib/library-admin';

	// A period-over-period change chip for a dashboard stat tile. Good reads in
	// the accent, bad in danger, no-change stays muted; the arrow carries the
	// direction so it doesn't lean on colour alone. A decline is bad unless the
	// trend says otherwise (`bad`), which a falling zero-result rate does.
	// Renders nothing when there's no baseline to compare (trend === null).
	let { trend, title = 'Change vs the previous period' }: { trend: Trend; title?: string } =
		$props();
	const tone = $derived(
		!trend || trend.dir === 'flat'
			? 'text-muted'
			: (trend.bad ?? trend.dir === 'down')
				? 'text-danger'
				: 'text-accent'
	);
</script>

{#if trend}
	<span
		class="text-small font-semibold tabular-nums {tone}"
		{title}
	>
		{trend.dir === 'up' ? '↑' : trend.dir === 'down' ? '↓' : ''}{trend.text}
	</span>
{/if}
