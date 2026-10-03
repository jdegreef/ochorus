<!--
	The content audit's chapter-length histogram: every non-empty chapter in the
	edition in view, bucketed by word count, with the Tiny and Giant thresholds
	drawn as lines on the bucket edges they sit on. It answers "are the
	thresholds in the right place?" — how much of the library each line cuts
	off, and whether the flagged tail hugs the line or runs far past it.

	Edges, counts and both thresholds come from the API (backend `qa.py`), so a
	moved threshold moves the line and the amber bars with it. Inline SVG laid
	out in pixels from the measured width (text never scales); below MIN_W it
	keeps MIN_W and scrolls inside its own box, never the page.
-->
<script lang="ts">
	import type { ChapterLengths } from '$lib/library-admin';
	import { edgeSlot, lengthBuckets } from '$lib/chapterLengths';

	let { data }: { data: ChapterLengths } = $props();

	const nf = new Intl.NumberFormat('en');
	const sum = (xs: number[]) => xs.reduce((n, x) => n + x, 0);

	const buckets = $derived(lengthBuckets(data));
	const total = $derived(sum(data.counts));
	const max = $derived(Math.max(1, ...buckets.map((b) => b.count)));
	const flaggedCount = (flag: 'tiny' | 'giant') => sum(buckets.filter((b) => b.flag === flag).map((b) => b.count));
	const tinyCount = $derived(flaggedCount('tiny'));
	const giantCount = $derived(flaggedCount('giant'));

	// Geometry (px). The top band holds the threshold labels so they never
	// collide with a bar's count; the bottom band holds the bucket labels.
	const MIN_W = 640;
	const TOP = 18; // threshold-label band
	const COUNT = 16; // count label above the tallest bar
	const PLOT = 132; // tallest bar
	const AXIS = 22; // bucket-label band
	const H = TOP + COUNT + PLOT + AXIS;
	const BASE = TOP + COUNT + PLOT; // the baseline's y
	const BAR_MAX = 28;
	const R = 4; // rounded data-end, square at the baseline

	let measured = $state(0);
	const W = $derived(Math.max(MIN_W, measured));
	const slot = $derived(W / buckets.length);
	const barW = $derived(Math.min(BAR_MAX, slot - 8));
	const cx = (i: number) => slot * i + slot / 2;

	const barH = (count: number) => (count ? Math.max(3, (count / max) * PLOT) : 0);
	// A column with a rounded top and a square foot.
	function barPath(i: number, h: number) {
		const x = cx(i) - barW / 2;
		const r = Math.min(R, h, barW / 2);
		const y = BASE - h;
		return `M${x},${BASE}V${y + r}Q${x},${y} ${x + r},${y}H${x + barW - r}Q${x + barW},${y} ${x + barW},${y + r}V${BASE}Z`;
	}

	const thresholds = $derived(
		[
			{ key: 'tiny', slot: edgeSlot(data, data.tiny_max), label: `${nf.format(data.tiny_max)} · tiny` },
			{ key: 'giant', slot: edgeSlot(data, data.giant_min), label: `${nf.format(data.giant_min)} · giant` }
		]
			.filter((t) => t.slot > 0)
			.map((t) => {
				const x = slot * t.slot;
				// The flagged side: left of the tiny line, right of the giant one.
				return { ...t, x, zone: t.key === 'tiny' ? { x: 0, w: x } : { x, w: W - x } };
			})
	);

	const summary = $derived(
		`Chapter lengths, ${nf.format(total)} chapters: ${nf.format(tinyCount)} under ${nf.format(data.tiny_max)} words (tiny), ` +
			`${nf.format(giantCount)} over ${nf.format(data.giant_min)} words (giant). Every bucket is in the table below.`
	);
</script>

<div class="rounded-card border border-border bg-surface p-4">
	<h3 class="text-body font-semibold text-text">Chapter length</h3>
	<p class="mb-3 text-small text-muted">Chapters by length. Amber bars are flagged (accepted findings still count here).</p>
	<div class="scroller overflow-x-auto" bind:clientWidth={measured}>
		<svg width={W} height={H} viewBox="0 0 {W} {H}" role="img" aria-label={summary} class="block">
			<!-- A faint wash over each flagged side of a line: the giant tail's
			     bars are a few pixels tall at this scale, so the zone carries
			     "flagged" where the bar colour alone is too small to read. -->
			{#each thresholds as t (t.key)}
				<rect x={t.zone.x} y={TOP - 12} width={t.zone.w} height={BASE - TOP + 12} class="cl-zone" />
			{/each}
			<line x1="0" x2={W} y1={BASE + 0.5} y2={BASE + 0.5} class="cl-axis" />
			{#each buckets as b, i (b.label)}
				{@const h = barH(b.count)}
				<g>
					<title>{b.range}: {nf.format(b.count)} {b.count === 1 ? 'chapter' : 'chapters'}{b.flag ? ` · flagged ${b.flag}` : ''}</title>
					<!-- Hit target: the whole column, not just the bar. -->
					<rect x={slot * i} y={TOP} width={slot} height={BASE - TOP} fill="transparent" />
					{#if h}<path d={barPath(i, h)} class={b.flag ? 'cl-bar-flagged' : 'cl-bar'} />{/if}
					<text x={cx(i)} y={BASE - h - 4} text-anchor="middle" class="cl-count">{nf.format(b.count)}</text>
					<text x={cx(i)} y={BASE + 15} text-anchor="middle" class="cl-tick">{b.label}</text>
				</g>
			{/each}
			{#each thresholds as t (t.key)}
				{@const x = Math.round(t.x) + 0.5}
				<line x1={x} x2={x} y1={TOP - 12} y2={BASE} class="cl-threshold" />
				<text x={x + 4} y={TOP - 4} class="cl-threshold-label">{t.label}</text>
			{/each}
		</svg>
	</div>
	<!-- The chart's table twin, for screen readers (the SVG is one image). -->
	<table class="sr-only">
		<caption>Chapters by length</caption>
		<thead><tr><th scope="col">Length</th><th scope="col">Chapters</th><th scope="col">Flagged</th></tr></thead>
		<tbody>
			{#each buckets as b (b.label)}
				<tr><th scope="row">{b.range}</th><td>{nf.format(b.count)}</td><td>{b.flag ?? 'no'}</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	/* The box takes its width from the page, never from the SVG inside it —
	   otherwise the chart's MIN_W would widen the page's grid track on a phone
	   instead of scrolling here. */
	.scroller {
		contain: inline-size;
	}
	svg {
		font-variant-numeric: tabular-nums;
	}
	.cl-bar {
		/* Neutral, a step toward the card so the flagged bars lead. */
		fill: color-mix(in srgb, var(--border-strong) 70%, var(--surface));
	}
	.cl-bar-flagged {
		fill: var(--warning);
	}
	.cl-zone {
		fill: color-mix(in srgb, var(--warning) 7%, transparent);
	}
	.cl-axis {
		stroke: var(--border);
		stroke-width: 1;
	}
	.cl-threshold {
		stroke: var(--muted);
		stroke-width: 1;
		stroke-dasharray: 3 3;
	}
	.cl-count,
	.cl-tick,
	.cl-threshold-label {
		fill: var(--text);
		font-size: var(--fs-micro);
	}
	.cl-tick {
		fill: var(--muted);
	}
	.cl-threshold-label {
		font-weight: 600;
	}
</style>
