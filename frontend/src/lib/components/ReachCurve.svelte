<script lang="ts">
	import type { AdminBookChapter, AdminReachPoint, AdminSteepestDrop } from '$lib/library-admin';

	// Where readers stop, for one book edition: a bar per chapter for the readers
	// who reached it, its foot shaded for those still reading there, and under
	// it the chapter's length (gold when the content checks flag it). The
	// steepest drop is named in words above the bars, because the point of the
	// chart is "which chapter, and is it broken", not the shape alone.
	let {
		reach,
		chapters,
		steepest,
		chapterHref
	}: {
		reach: AdminReachPoint[];
		chapters: AdminBookChapter[];
		steepest: AdminSteepestDrop | null;
		chapterHref: (order: number) => string;
	} = $props();

	const nf = new Intl.NumberFormat('en');
	const top = $derived(Math.max(1, ...reach.map((p) => p.reached)));
	const longest = $derived(Math.max(1, ...chapters.map((c) => c.word_count)));
	const byOrder = $derived(new Map(chapters.map((c) => [c.order, c])));
	const cliff = $derived(steepest ? byOrder.get(steepest.chapter) : undefined);
	const pct = (n: number) => `${Math.round(n * 100)}%`;
	const tip = (p: AdminReachPoint) => {
		const c = byOrder.get(p.chapter);
		return [
			`Chapter ${p.chapter}${c?.title ? ` · ${c.title}` : ''}`,
			`${nf.format(p.reached)} reached it · ${nf.format(p.stopped)} stopped here · ${nf.format(p.still)} still reading here`,
			c ? `${nf.format(c.word_count)} words${c.flags.length ? ` · flagged ${c.flags.join(', ')}` : ''}` : ''
		]
			.filter(Boolean)
			.join('\n');
	};
</script>

{#if reach[0]?.reached}
	<div class="mb-4 rounded-card border border-border p-4">
		<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
			<h3 class="text-body font-semibold text-text">Where readers stop</h3>
			<span class="text-small text-muted">{nf.format(reach[0].reached)} reader{reach[0].reached === 1 ? '' : 's'} · stopped = no progress for 30 days</span>
		</div>
		{#if steepest}
			<p class="mb-3 text-small">
				<span class="font-semibold text-danger">{pct(steepest.rate)} stop at chapter {steepest.chapter}</span>
				<span class="text-muted">
					({nf.format(steepest.stopped)} of {nf.format(steepest.reached)}){#if cliff?.flags.length}{` · flagged ${cliff.flags.join(', ')}, likely an import problem`}{/if}
				</span>
				<a href={chapterHref(steepest.chapter)} class="ms-1 text-accent hover:underline">Open chapter</a>
			</p>
		{/if}
		<div class="flex items-end gap-1 overflow-x-auto pb-1" role="list" aria-label="Readers who reached each chapter">
			{#each reach as p (p.chapter)}
				{@const c = byOrder.get(p.chapter)}
				{@const isCliff = steepest?.chapter === p.chapter}
				<div class="flex min-w-6 flex-1 flex-col items-center gap-1" role="listitem" title={tip(p)} aria-label={tip(p)}>
					<span class="text-micro tabular-nums text-muted">{p.reached}</span>
					<div class="flex h-28 w-full flex-col justify-end">
						<div
							class="flex w-full flex-col justify-end overflow-hidden rounded-t-sm {isCliff ? 'ring-2 ring-danger' : ''}"
							style="height: {(p.reached / top) * 100}%; min-height: {p.reached ? '2px' : '0'}"
						>
							<div class="w-full flex-1 bg-accent"></div>
							{#if p.still}
								<div class="w-full border border-accent bg-accent-soft" style="height: {(p.still / p.reached) * 100}%"></div>
							{/if}
						</div>
					</div>
					<div class="flex h-1.5 w-full items-center justify-center">
						<div
							class="h-full rounded-sm {c?.flags.length ? 'bg-gold' : 'bg-border-strong'}"
							style="width: {Math.max(8, ((c?.word_count ?? 0) / longest) * 100)}%"
						></div>
					</div>
					<span class="text-micro tabular-nums {c?.flags.length ? 'font-semibold text-warning' : 'text-muted'}">{p.chapter}</span>
				</div>
			{/each}
		</div>
		<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-micro text-muted">
			<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-3 rounded-sm bg-accent"></span>reached</span>
			<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-3 rounded-sm border border-accent bg-accent-soft"></span>still reading there</span>
			<span class="inline-flex items-center gap-1.5"><span class="h-1.5 w-3 rounded-sm bg-border-strong"></span>chapter length (gold = flagged)</span>
		</div>
	</div>
{/if}
