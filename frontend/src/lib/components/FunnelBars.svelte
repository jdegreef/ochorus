<script lang="ts">
	// A funnel as bar rows: label, bar, count and share. Every bar and share is
	// of the FIRST step, so the drop-off reads straight down the bars. Shared by
	// the admin funnels (reading plans; sign-up to habit) so they read alike.
	let { steps }: { steps: { label: string; count: number }[] } = $props();

	const nf = new Intl.NumberFormat('en');
	const rows = $derived.by(() => {
		const base = steps[0]?.count ?? 0;
		if (!base) return [];
		return steps.map((st, i) => {
			const pct = Math.round((st.count / base) * 100);
			// The separator lives with the share, so the markup has no
			// whitespace for Svelte to trim ("26· 81%").
			return { ...st, pct, note: i ? ` · ${pct}%` : '' };
		});
	});
</script>

<!-- One grid for every row, so the label column is as wide as the longest
     label on THIS funnel and the bars line up beneath each other. -->
<div class="grid grid-cols-[max-content_1fr_auto] items-center gap-x-3 gap-y-2">
	{#each rows as r, i (i)}
		<span class="text-small text-text">{r.label}</span>
		<div class="h-4 overflow-hidden rounded-full bg-surface-2">
			<div class="h-full rounded-full bg-accent-soft" style="width: {r.pct}%"></div>
		</div>
		<span class="text-end text-small tabular-nums text-muted">
			<span class="font-semibold text-text">{nf.format(r.count)}</span>{r.note}
		</span>
	{/each}
</div>
