<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { buildHeatmap } from '$lib/heatmap';

	// Pure/prop-driven: `days` is the activity log, `today` the reader's local
	// date, `locale` for month/weekday names. A read day's shade is the streak
	// tier its unbroken run had reached (streak.ts, runLevel); the golds are the
	// `.heat` rules in app.css. Weeks default to ~6 months, which
	// shows a meaningful pattern without a vast empty grid for new readers.
	let {
		days,
		today,
		locale = 'en',
		weeks = 26,
		runsFrom = undefined
	}: {
		days: string[];
		today: string;
		locale?: string;
		weeks?: number;
		/** The log runs are measured over, when `days` is a slice of it (Year in
		 *  Books draws one year but a run may have begun the December before). */
		runsFrom?: string[];
	} = $props();

	const t = i18n.t;
	const grid = $derived(buildHeatmap(days, today, weeks, locale, runsFrom ?? days));

	// Month label keyed by its starting column, for O(1) lookup while rendering.
	const monthByCol = $derived(new Map(grid.monthLabels.map((mo) => [mo.col, mo.label])));

	// Mon / Wed / Fri row labels for orientation (rows 1, 3, 5; row 0 = Sunday).
	const rowLabel = $derived.by(() => {
		const map = new Map<number, string>();
		for (const r of [1, 3, 5]) {
			map.set(
				r,
				new Date(grid.weeks[0][r].iso + 'T00:00:00Z').toLocaleDateString(locale, {
					weekday: 'short',
					timeZone: 'UTC'
				})
			);
		}
		return map;
	});

	const readCount = $derived(days.filter((d) => d <= today).length);

	// When the year is wider than its column, it opens on THIS week, not on
	// last year's: the scroller starts at the end where today is (the far left
	// in a right-to-left page, where modern browsers count scrollLeft down
	// from 0). Re-run when the grid changes width.
	function showLatest(el: HTMLElement, _weeks: number) {
		const go = () => {
			const rtl = getComputedStyle(el).direction === 'rtl';
			el.scrollLeft = rtl ? -el.scrollWidth : el.scrollWidth;
		};
		go();
		return { update: go };
	}

	function cellTitle(iso: string, read: boolean): string {
		const d = new Date(iso + 'T00:00:00Z').toLocaleDateString(locale, {
			dateStyle: 'medium',
			timeZone: 'UTC'
		});
		return read ? `${d} — ${t('settings.heatmapRead')}` : d;
	}
</script>

<!-- One CSS grid drives the whole calendar so the month row, weekday column and
     day cells stay aligned to a single geometry. The week columns grow to fill
     the width (1fr) but never shrink below --min-cell; below that the grid
     scrolls on its own rather than pushing the page sideways. Cells are square
     via aspect-ratio, so they scale with the column. -->
<div
	class="w-full overflow-x-auto"
	use:showLatest={weeks}
	role="img"
	aria-label="{t('settings.heatmapTitle')}: {readCount} {t('settings.streakDaysRead')}"
>
	<div
		class="grid items-center"
		style="--gap: 3px; --wd: 2rem; --min-cell: 0.72rem; gap: var(--gap);
		       grid-template-columns: var(--wd) repeat({weeks}, minmax(var(--min-cell), 1fr))"
	>
		<!-- Month labels row: a spacer over the weekday column, then one cell per
		     week, labelled only where a month begins. -->
		<div></div>
		{#each grid.weeks as _, w (w)}
			<div class="whitespace-nowrap text-micro leading-none text-muted">
				{monthByCol.get(w) ?? ''}
			</div>
		{/each}

		<!-- Seven weekday rows: the label in column one, then a cell per week. -->
		{#each Array(7) as _, r (r)}
			<div class="whitespace-nowrap text-micro leading-none text-muted">{rowLabel.get(r) ?? ''}</div>
			{#each grid.weeks as col, w (w)}
				{@const cell = col[r]}
				{#if cell.future}
					<div style="aspect-ratio: 1" aria-hidden="true"></div>
				{:else}
					<div
						class="heat rounded-[2px]"
						data-level={cell.level}
						style="aspect-ratio: 1"
						title={cellTitle(cell.iso, cell.read)}
						aria-hidden="true"
					></div>
				{/if}
			{/each}
		{/each}
	</div>

	<!-- Legend: unread, then the four run shades. Sticky at the start edge, so
	     it stays in view while the year beside it is scrolled to today. -->
	<div class="sticky start-0 mt-2 flex flex-wrap items-center gap-1.5 text-micro text-muted">
		<span class="heat heat-swatch rounded-[2px]" data-level="0"></span>
		<span>{t('settings.heatmapNone')}</span>
		<span class="ms-2 inline-flex gap-0.5">
			{#each [1, 2, 3, 4] as level (level)}
				<span class="heat heat-swatch rounded-[2px]" data-level={level}></span>
			{/each}
		</span>
		<span>{t('settings.heatmapRead')} · {t('settings.heatmapDeeper')}</span>
	</div>
</div>

