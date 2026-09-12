<script lang="ts">
	import type { Trend } from '$lib/library-admin';

	// A period-over-period change chip for a dashboard stat tile. Up reads in the
	// accent, a decline in danger, no-change stays muted; the arrow carries the
	// direction so it doesn't lean on colour alone. Renders nothing when there's
	// no baseline to compare (trend === null).
	let { trend, title = 'Change vs the previous period' }: { trend: Trend; title?: string } =
		$props();
</script>

{#if trend}
	<span
		class="text-small font-semibold tabular-nums {trend.dir === 'up'
			? 'text-accent'
			: trend.dir === 'down'
				? 'text-danger'
				: 'text-muted'}"
		{title}
	>
		{trend.dir === 'up' ? '↑' : trend.dir === 'down' ? '↓' : ''}{trend.text}
	</span>
{/if}
