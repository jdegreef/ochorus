<script lang="ts">
	import ColumnChart, { type Column } from '$lib/components/ColumnChart.svelte';
	import { chapterFlagLabel, type AdminBookChapter, type AdminReachPoint, type AdminSteepestDrop } from '$lib/library-admin';

	// Where readers stop, for one book edition: a bar per chapter for the readers
	// who reached it, its dark foot those still reading there, and under it the
	// chapter's length (gold when the content checks flag it). The steepest drop
	// is named in words above the bars, because the point of the chart is
	// "which chapter, and is it broken", not the shape alone.
	let {
		reach,
		chapters,
		steepest,
		stallDays,
		chapterHref
	}: {
		reach: AdminReachPoint[];
		chapters: AdminBookChapter[];
		steepest: AdminSteepestDrop | null;
		stallDays: number;
		chapterHref: (order: number) => string;
	} = $props();

	const nf = new Intl.NumberFormat('en');
	const pct = (n: number) => `${Math.round(n * 100)}%`;
	const top = $derived(reach[0]?.reached ?? 0);
	const longest = $derived(Math.max(1, ...chapters.map((c) => c.word_count)));
	const byOrder = $derived(new Map(chapters.map((c) => [c.order, c])));
	const flagsOf = (order: number) => (byOrder.get(order)?.flags ?? []).map(chapterFlagLabel);

	const columns = $derived<Column[]>(
		reach.map((p) => {
			const c = byOrder.get(p.chapter);
			const flags = flagsOf(p.chapter);
			return {
				key: String(p.chapter),
				label: String(p.chapter),
				value: p.reached,
				part: p.still,
				highlight: steepest?.chapter === p.chapter,
				title: [
					`Chapter ${p.chapter}${c?.title ? ` · ${c.title}` : ''}`,
					`${nf.format(p.reached)} reached it · ${nf.format(p.stopped)} stopped here · ${nf.format(p.still)} still reading here`,
					c ? `${nf.format(c.word_count)} words${flags.length ? ` · flagged ${flags.join(', ')}` : ''}` : ''
				]
					.filter(Boolean)
					.join('\n')
			};
		})
	);
</script>

{#if top}
	<div class="mb-4 rounded-card border border-border p-4">
		<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
			<h3 class="text-body font-semibold text-text">Where readers stop</h3>
			<span class="text-small text-muted">{nf.format(top)} reader{top === 1 ? '' : 's'} · stopped = no progress for {stallDays} days</span>
		</div>
		{#if steepest}
			{@const flags = flagsOf(steepest.chapter)}
			<p class="mb-3 text-small">
				<span class="font-semibold text-danger">{pct(steepest.rate)} stop at chapter {steepest.chapter}</span>
				<span class="text-muted">
					({nf.format(steepest.stopped)} of {nf.format(steepest.reached)}){#if flags.length}{` · flagged ${flags.join(', ')}, likely an import problem`}{/if}
				</span>
				<a href={chapterHref(steepest.chapter)} class="ms-1 text-accent hover:underline">Open chapter</a>
			</p>
		{/if}
		<!-- A long book scrolls sideways rather than squeezing its bars to slivers. -->
		<div class="overflow-x-auto pb-1">
			<div style="min-width: {reach.length * 1.75}rem">
				<ColumnChart {columns} height="9rem">
					{#snippet foot(col)}
						{@const c = byOrder.get(Number(col.key))}
						<div class="flex h-1.5 w-full items-center justify-center">
							<div
								class="h-full rounded-sm {c?.flags.length ? 'bg-gold' : 'bg-border-strong'}"
								style="width: {Math.max(8, ((c?.word_count ?? 0) / longest) * 100)}%"
							></div>
						</div>
					{/snippet}
				</ColumnChart>
			</div>
		</div>
		<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-micro text-muted">
			<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-3 rounded-sm bg-accent-soft"></span>reached</span>
			<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-3 rounded-sm bg-accent"></span>still reading there</span>
			<span class="inline-flex items-center gap-1.5"><span class="h-1.5 w-3 rounded-sm bg-border-strong"></span>chapter length (gold = flagged)</span>
		</div>
	</div>
{/if}
