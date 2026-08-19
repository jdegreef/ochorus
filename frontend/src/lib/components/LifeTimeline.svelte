<script lang="ts">
	/**
	 * A slim lifespan timeline: the author's life drawn as an accent segment on a
	 * century-scale axis, so a reader instantly places them in history rather than
	 * parsing two bare years. Pure computation from birth/death years — renders
	 * nothing without both.
	 */
	interface Props {
		birthYear: number | null;
		deathYear: number | null;
	}
	let { birthYear, deathYear }: Props = $props();

	// The axis spans whole centuries bracketing the life, so the gridlines are
	// round years (1800, 1900, …) the segment sits between.
	const domain = $derived.by(() => {
		if (birthYear == null || deathYear == null || deathYear < birthYear) return null;
		const start = Math.floor(birthYear / 100) * 100;
		const end = Math.ceil(deathYear / 100) * 100;
		// A life wholly inside one century still needs a full century of axis.
		return { start, end: end === start ? start + 100 : end };
	});

	const pct = (year: number) =>
		domain ? ((year - domain.start) / (domain.end - domain.start)) * 100 : 0;

	// Century gridlines strictly inside the domain (the ends are the edges).
	const ticks = $derived.by(() => {
		if (!domain) return [];
		const out: number[] = [];
		for (let y = domain.start; y <= domain.end; y += 100) out.push(y);
		return out;
	});
</script>

{#if domain && birthYear != null && deathYear != null}
	<div class="life-timeline mx-auto mt-6 max-w-[40rem]" aria-hidden="true">
		<div class="track">
			{#each ticks as y (y)}
				<span class="tick" style="left: {pct(y)}%">
					<span class="tick-label">{y}</span>
				</span>
			{/each}
			<span class="span" style="left: {pct(birthYear)}%; right: {100 - pct(deathYear)}%">
				<span class="dot start"></span>
				<span class="dot end"></span>
			</span>
			<span class="year year-start" style="left: {pct(birthYear)}%">{birthYear}</span>
			<span class="year year-end" style="left: {pct(deathYear)}%">{deathYear}</span>
		</div>
	</div>
{/if}

<style>
	.track {
		position: relative;
		height: 3.5rem;
		margin-top: 1.25rem;
	}
	/* Century baseline. */
	.track::before {
		content: '';
		position: absolute;
		inset-inline: 0;
		top: 1.6rem;
		height: 2px;
		background: var(--border);
		border-radius: 2px;
	}
	.tick {
		position: absolute;
		top: 1.2rem;
		width: 1px;
		height: 0.8rem;
		background: var(--border);
		transform: translateX(-0.5px);
	}
	/* The chart is chronological, and every position in it is a percentage of
	   elapsed time written as an inline `left:` by the markup above — so these
	   rules are physical to MATCH those, and a logical property here would put
	   the tick labels and end dots somewhere the spans aren't. Earlier-is-left
	   is a property of the chart, not of the prose around it. */
	.tick-label {
		position: absolute;
		top: 1.1rem;
		left: 50%; /* rtl-ok: paired with the inline left:%% positions above */
		transform: translateX(-50%);
		font-size: 0.7rem;
		color: var(--muted);
		white-space: nowrap;
	}
	/* The life: an accent segment over the baseline. */
	.span {
		position: absolute;
		top: 1.45rem;
		height: 5px;
		background: var(--accent);
		border-radius: 999px;
	}
	.dot {
		position: absolute;
		top: 50%;
		width: 9px;
		height: 9px;
		border-radius: 999px;
		background: var(--accent);
		transform: translate(-50%, -50%);
	}
	.dot.start {
		left: 0; /* rtl-ok: chart coordinate, see .tick-label */
	}
	.dot.end {
		left: 100%; /* rtl-ok: chart coordinate, see .tick-label */
	}
	.year {
		position: absolute;
		top: 0;
		font-family: var(--font-display);
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text);
	}
	.year-start {
		transform: translateX(-50%);
	}
	.year-end {
		transform: translateX(-50%);
	}
</style>
