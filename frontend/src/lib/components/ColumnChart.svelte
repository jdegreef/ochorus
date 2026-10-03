<!--
	The admin pages' small column chart: a count above each bar, a label below,
	bars scaled to the series max. Shared because three pages hand-rolled it and
	all three had the same layout bug — each bar's percentage height resolved
	against a column with no definite height, so every bar collapsed to its 3px
	floor. The fix lives here once: the column fills the chart's height and the
	bar sits in a `flex-1` slot that gives the percentage something to measure.

	`part` draws an optional darker segment at the bottom of a bar (the search
	page's zero-result share), as a count out of the bar's `value`. `current`
	outlines a bar whose period is still in progress, so a partial count doesn't
	read as a drop against the full periods beside it. `highlight` rings the one
	bar the page is pointing at (a book's steepest drop), and `foot` draws a
	small mark under each bar, above its label (that chapter's length).
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	export type Column = {
		key: string;
		label: string;
		value: number;
		part?: number;
		current?: boolean;
		highlight?: boolean;
		title?: string;
	};

	let {
		columns,
		height = '8rem',
		foot
	}: { columns: Column[]; height?: string; foot?: Snippet<[Column]> } = $props();

	const max = $derived(Math.max(1, ...columns.map((c) => c.value)));
	const nf = new Intl.NumberFormat('en');
</script>

<div class="flex items-end gap-1.5 sm:gap-2" style="height: {height}">
	{#each columns as c (c.key)}
		<div class="flex h-full min-w-0 flex-1 flex-col items-center gap-1" title={c.title}>
			<div class="text-small tabular-nums text-muted">{nf.format(c.value)}</div>
			<div class="flex w-full flex-1 flex-col justify-end">
				<div
					class="flex w-full flex-col justify-end overflow-hidden rounded-t-sm"
					class:current={c.current}
					class:ring-2={c.highlight}
					class:ring-danger={c.highlight}
					style="height: {(c.value / max) * 100}%; min-height: {c.value ? '3px' : '0'}"
				>
					<div class="w-full flex-1 {c.current ? '' : 'bg-accent-soft'}"></div>
					{#if c.part}
						<div class="w-full bg-accent" style="height: {(c.part / c.value) * 100}%"></div>
					{/if}
				</div>
			</div>
			{@render foot?.(c)}
			<div class="text-center text-micro leading-tight text-muted">{c.label}</div>
		</div>
	{/each}
</div>

<style>
	.current {
		border: 1px dashed var(--accent);
		border-bottom: 0;
	}
</style>
