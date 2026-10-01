<script lang="ts">
	// A small column chart for the admin dashboards: one bar per period, its
	// count above it and its label below. Shared so the three copies on the
	// engagement, users and search pages can't drift apart (they did).
	//
	// Each bar is a share of a FIXED-height track, less room for its count. All
	// three copies once sized the bar as a % of a content-sized column, which
	// resolves to auto, so every bar fell to its 3px min-height whatever the
	// count.
	export type ColumnBar = {
		key: string;
		label: string;
		value: number;
		/** A highlighted share of the bar, drawn stacked at its foot. */
		part?: number;
		title?: string;
	};

	let { bars, current = false }: { bars: ColumnBar[]; current?: boolean } = $props();

	const max = $derived(Math.max(1, ...bars.map((b) => b.value)));
</script>

<div class="flex gap-2">
	{#each bars as b, i (b.key)}
		{@const inProgress = current && i === bars.length - 1}
		<div class="flex min-w-0 flex-1 flex-col items-center gap-1" title={b.title}>
			<div class="flex h-32 w-full flex-col justify-end">
				<div class="text-center text-small tabular-nums text-muted">{b.value || ''}</div>
				<div
					class="flex w-full flex-col justify-end overflow-hidden rounded-t-sm {inProgress ? 'in-progress' : 'bg-accent-soft'}"
					style="height: calc((100% - 1.5rem) * {b.value / max}); min-height: {b.value ? '3px' : '0'}"
				>
					{#if b.part}
						<div class="w-full bg-accent" style="height: {(b.part / b.value) * 100}%"></div>
					{/if}
				</div>
			</div>
			<div class="text-micro text-muted">{b.label}</div>
		</div>
	{/each}
</div>
{#if current}
	<p class="mt-2 text-micro text-muted">The last bar is still in progress.</p>
{/if}

<style>
	/* A period still in progress: outlined, so a partial count doesn't read as
	   a drop against the full periods beside it. */
	.in-progress {
		border: 1px dashed var(--accent);
		border-bottom: 0;
	}
</style>
