<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { buildHeatmap } from '$lib/heatmap';

	// Pure/prop-driven: `days` is the activity log, `today` the reader's local
	// date, `locale` for month/weekday names. Weeks default to ~6 months, which
	// shows a meaningful pattern without a vast empty grid for new readers.
	let {
		days,
		today,
		locale = 'en',
		weeks = 26
	}: { days: string[]; today: string; locale?: string; weeks?: number } = $props();

	const t = i18n.t;
	const grid = $derived(buildHeatmap(days, today, weeks, locale));

	// Mon / Wed / Fri row labels for orientation (rows 1, 3, 5; row 0 = Sunday).
	const rowLabels = $derived(
		[1, 3, 5].map((r) => ({
			r,
			label: new Date(grid.weeks[0][r].iso + 'T00:00:00Z').toLocaleDateString(locale, {
				weekday: 'short',
				timeZone: 'UTC'
			})
		}))
	);

	const readCount = $derived(days.filter((d) => d <= today).length);

	function cellTitle(iso: string, read: boolean): string {
		const d = new Date(iso + 'T00:00:00Z').toLocaleDateString(locale, {
			dateStyle: 'medium',
			timeZone: 'UTC'
		});
		return read ? `${d} — ${t('settings.heatmapRead')}` : d;
	}
</script>

<!-- The grid can be wider than the panel on small screens; let it scroll on its
     own rather than pushing the page sideways. --cell/--gap keep the month row,
     weekday column, and day cells aligned to one geometry. -->
<div
	class="overflow-x-auto"
	style="--cell: 0.72rem; --gap: 3px; --wd: 2rem"
	role="img"
	aria-label="{t('settings.heatmapTitle')}: {readCount} {t('settings.streakDaysRead')}"
>
	<div class="inline-block">
		<!-- Month labels, aligned over their starting column. -->
		<div class="flex" style="gap: var(--gap); padding-inline-start: calc(var(--wd) + var(--gap))">
			{#each grid.weeks as _, w (w)}
				{@const m = grid.monthLabels.find((x) => x.col === w)}
				<div class="text-[0.62rem] leading-none text-muted" style="width: var(--cell)">
					{m ? m.label : ''}
				</div>
			{/each}
		</div>

		<!-- Weekday column + week columns. -->
		<div class="mt-1 flex" style="gap: var(--gap)">
			<div class="flex flex-col" style="gap: var(--gap); width: var(--wd)">
				{#each Array(7) as _, r (r)}
					{@const rl = rowLabels.find((x) => x.r === r)}
					<div
						class="text-[0.62rem] leading-none text-muted"
						style="height: var(--cell); line-height: var(--cell)"
					>
						{rl ? rl.label : ''}
					</div>
				{/each}
			</div>

			{#each grid.weeks as col, w (w)}
				<div class="flex flex-col" style="gap: var(--gap)">
					{#each col as cell (cell.iso)}
						{#if cell.future}
							<div style="width: var(--cell); height: var(--cell)" aria-hidden="true"></div>
						{:else}
							<div
								class="rounded-[2px] {cell.read ? 'bg-gold' : 'bg-surface-2'}"
								style="width: var(--cell); height: var(--cell)"
								title={cellTitle(cell.iso, cell.read)}
								aria-hidden="true"
							></div>
						{/if}
					{/each}
				</div>
			{/each}
		</div>

		<!-- Legend -->
		<div class="mt-2 flex items-center gap-1.5 text-[0.68rem] text-muted">
			<span class="inline-block rounded-[2px] bg-surface-2" style="width: 0.66rem; height: 0.66rem"
			></span>
			<span>{t('settings.heatmapNone')}</span>
			<span
				class="ms-2 inline-block rounded-[2px] bg-gold"
				style="width: 0.66rem; height: 0.66rem"
			></span>
			<span>{t('settings.heatmapRead')}</span>
		</div>
	</div>
</div>
